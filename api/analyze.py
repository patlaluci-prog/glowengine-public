import os
import cv2
import queue
import logging
import asyncio
import numpy as np

from io import BytesIO
from PIL import Image
from PIL.Image import DecompressionBombError

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse

from security.rate_limit import check_rate_limit

from core.features import (
    process_face_mesh,
    compute_features,
    db_check_duplicate_hybrid
)

from workers.writer import db_write_queue
from workers.executors import MEDIAPIPE_EXECUTOR

from core.scoring import (
    get_centralized_model,
    predict_score
)

from config import (
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_SIZE,
    MAX_RAW_FILE_SIZE,
    MAX_PIXELS,
    MAX_IMAGE_DIMENSION
)

router = APIRouter()
logger = logging.getLogger("ai_engine")


def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("")
async def analyze_face(request: Request, file: UploadFile = File(...)):
    loop = asyncio.get_running_loop()

    client_ip = get_client_ip(request)

    await loop.run_in_executor(
        None,
        check_rate_limit,
        client_ip
    )

    try:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Invalid content type"
            )

        _, ext = os.path.splitext(
            (file.filename or "").lower()
        )

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported extension"
            )

        buffer = bytearray()
        while chunk := await file.read(1024 * 1024):
            if len(buffer) + len(chunk) > MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="Too large"
                )
            buffer.extend(chunk)

        if len(buffer) > MAX_RAW_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Raw file too large"
            )

        try:
            with Image.open(BytesIO(buffer)) as img:
                img.verify()

            with Image.open(BytesIO(buffer)) as img:
                if (
                    img.width * img.height > MAX_PIXELS
                    or img.width > MAX_IMAGE_DIMENSION
                    or img.height > MAX_IMAGE_DIMENSION
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Dimensions exceeded"
                    )
                img = img.convert("RGB")

        except DecompressionBombError:
            raise HTTPException(
                status_code=413,
                detail="Bomb detected"
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Corrupted image"
            )

        image = cv2.imdecode(
            np.frombuffer(buffer, dtype=np.uint8),
            cv2.IMREAD_COLOR
        )

        if image is None:
            raise HTTPException(
                status_code=400,
                detail="Image decode failed"
            )

        if (
            image.shape[0] > MAX_IMAGE_DIMENSION
            or image.shape[1] > MAX_IMAGE_DIMENSION
        ):
            raise HTTPException(
                status_code=400,
                detail="Decoded image too large"
            )

        rgb_image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2RGB
        )

        results = await loop.run_in_executor(
            MEDIAPIPE_EXECUTOR,
            process_face_mesh,
            rgb_image
        )

        if not results or not results.multi_face_landmarks:
            raise HTTPException(
                status_code=400,
                detail="No face detected"
            )

        landmarks = results.multi_face_landmarks[0]

        features = await loop.run_in_executor(
            None,
            compute_features,
            landmarks
        )

        is_duplicate = await loop.run_in_executor(
            None,
            db_check_duplicate_hybrid,
            features
        )

        if not is_duplicate:
            try:
                db_write_queue.put_nowait({
                    "type": "insert",
                    "features": features.tolist(),
                    "human_score": None
                })
            except queue.Full:
                logger.warning("DB queue full")

        weights, _, stats = await loop.run_in_executor(
            None,
            get_centralized_model
        )

        raw_score = await loop.run_in_executor(
            None,
            predict_score,
            features,
            weights,
            stats
        )

        score = round(raw_score, 2)

        labels = [
            "eye_harmony",
            "face_height",
            "facial_ratio",
            "symmetry",
            "jaw_balance",
            "mouth_ratio"
        ]

        sorted_idx = [
            int(i)
            for i in np.argsort(features)
        ]

        return JSONResponse(content={
            "score": score,
            "population_mean": round(
                stats["mean_score"],
                2
            ),
            "strengths": [
                labels[i]
                for i in sorted_idx[-2:]
            ],
            "weaknesses": [
                labels[i]
                for i in sorted_idx[:2]
            ]
        })

    finally:
        await file.close()

import asyncio
import logging

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from core.scoring import get_centralized_model, predict_score
from core.synthetic import generate_synthetic_face
from core.training import train_centralized_model_transactional
from schemas.train import TrainPayload
from security.auth import verify_api_key
from security.rate_limit import check_rate_limit


router = APIRouter()
logger = logging.getLogger("ai_engine")


def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/generate")
async def get_chaos_generate(request: Request):
    loop = asyncio.get_running_loop()
    client_ip = get_client_ip(request)

    await loop.run_in_executor(None, check_rate_limit, client_ip)

    features = await loop.run_in_executor(None, generate_synthetic_face)
    weights, _, stats = await loop.run_in_executor(None, get_centralized_model)
    score = await loop.run_in_executor(None, predict_score, features, weights, stats)

    return JSONResponse(
        content={
            "status": "success",
            "features": [round(float(value), 6) for value in features],
            "score": round(float(score), 4),
            "population_mean": round(float(stats["mean_score"]), 2),
        }
    )


@router.post("/train", dependencies=[Depends(verify_api_key)])
async def post_chaos_train(payload: TrainPayload, request: Request):
    loop = asyncio.get_running_loop()
    client_ip = get_client_ip(request)

    await loop.run_in_executor(None, check_rate_limit, client_ip)

    features = np.array(payload.features_list, dtype=np.float32)
    try:
        _, new_mean, new_count = await loop.run_in_executor(
            None,
            train_centralized_model_transactional,
            features,
            payload.ai_score,
            payload.human_score,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("GlowEngine chaos training failed")
        raise HTTPException(status_code=500, detail=str(exc))

    return JSONResponse(
        content={
            "status": "success",
            "message": "Vote processed and model updated",
            "telemetry": {
                "target_score": float(payload.human_score),
                "population_mean": round(float(new_mean), 4),
                "score_count": int(new_count),
            },
        }
    )

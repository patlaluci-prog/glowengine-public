import numpy as np
import mediapipe as mp
import threading
import json

from workers.writer import (
    build_signature,
    duplicate_cache_exists,
    duplicate_cache_add
)

from db.database import get_db_connection

thread_local = threading.local()
mp_face_mesh = mp.solutions.face_mesh


def get_thread_local_face_mesh():
    if not hasattr(thread_local, "face_mesh"):
        thread_local.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    return thread_local.face_mesh


def process_face_mesh(rgb_image):
    return get_thread_local_face_mesh().process(rgb_image)


def cleanup_thread_local_mesh():
    if hasattr(thread_local, "face_mesh"):
        try:
            thread_local.face_mesh.close()
        except Exception:
            pass
        del thread_local.face_mesh


# ⚡ rychlejší než np.linalg.norm
def fast_distance(p1, p2):
    d = p1 - p2
    return np.sqrt(d[0]*d[0] + d[1]*d[1] + d[2]*d[2])


def safe_normalize(value, min_val, max_val):
    if max_val - min_val < 1e-6:
        return 0.0
    return (value - min_val) / (max_val - min_val)


def compute_features(landmarks):
    if landmarks is None or not hasattr(landmarks, "landmark"):
        raise ValueError("Invalid landmarks input")

    lms = landmarks.landmark
    if len(lms) < 468:
        raise ValueError("Incomplete facial landmarks")

    idx = [33, 263, 1, 152, 234, 454, 13, 14, 172, 397]
    pts = {i: np.array([lms[i].x, lms[i].y, lms[i].z], dtype=np.float32) for i in idx}

    left_eye = pts[33]
    right_eye = pts[263]

    # 🔥 SCALE NORMALIZACE
    scale = fast_distance(left_eye, right_eye) + 1e-6

    nose = pts[1]
    chin = pts[152]
    left_cheek = pts[234]
    right_cheek = pts[454]
    mouth_top = pts[13]
    mouth_bottom = pts[14]
    jaw_left = pts[172]
    jaw_right = pts[397]

    eye_dist = fast_distance(left_eye, right_eye) / scale
    face_height = fast_distance(nose, chin) / scale
    face_width = fast_distance(left_cheek, right_cheek) / scale
    mouth_height = fast_distance(mouth_top, mouth_bottom) / scale
    jaw_width = fast_distance(jaw_left, jaw_right) / scale

    ratio = face_width / (face_height + 1e-6)
    jaw_ratio = jaw_width / (face_width + 1e-6)
    mouth_ratio = mouth_height / (face_height + 1e-6)

    mid_eye = (left_eye + right_eye) / 2
    symmetry_raw = fast_distance(nose, mid_eye) / scale
    symmetry = np.exp(-symmetry_raw * 3.0)

    features = np.array([
        safe_normalize(eye_dist, 0.8, 1.2),
        safe_normalize(face_height, 1.0, 2.5),
        safe_normalize(ratio, 0.5, 2.0),
        safe_normalize(symmetry, 0.0, 1.0),
        safe_normalize(jaw_ratio, 0.4, 1.2),
        safe_normalize(mouth_ratio, 0.01, 0.12)
    ], dtype=np.float32)

    features = np.clip(features, 0.0, 1.0)

    if not np.isfinite(features).all():
        raise ValueError("Non-finite features")

    return features


def db_check_duplicate_hybrid(features, threshold=0.02):
    signature = build_signature(features)

    if duplicate_cache_exists(signature):
        return True

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT features
            FROM chaos_db
            WHERE signature = ?
            LIMIT 5
            """,
            (signature,)
        )

        for row in cursor.fetchall():
            try:
                stored = np.array(json.loads(row[0]), dtype=np.float32)

                # ⚡ FAST FAIL
                if stored.shape != features.shape:
                    continue

                diff = features - stored

                if (diff * diff).sum() < (threshold * threshold):
                    duplicate_cache_add(signature)
                    return True

            except Exception:
                continue

    return False

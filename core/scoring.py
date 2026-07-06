import numpy as np
import json
import time

from threading import RLock

from db.database import (
    BASE_WEIGHTS,
    get_db_connection
)

from config import MODEL_CACHE_TTL


model_cache = {
    "timestamp": 0,
    "adaptive_weights": None,
    "history_count": 0,
    "stats": None
}

model_cache_lock = RLock()


def invalidate_model_cache():
    with model_cache_lock:
        model_cache["timestamp"] = 0


def get_final_weights(adaptive_weights):
    # 🔥 adaptivnější mix (rychlejší učení)
    blend = 0.6 + min(0.3, float(adaptive_weights.mean()))

    final_weights = (
        (1 - blend) * BASE_WEIGHTS
        + blend * adaptive_weights
    )

    final_weights /= max(np.sum(final_weights), 1e-6)

    return final_weights.astype(np.float32)


def get_centralized_model():
    current_time = time.time()

    # Zámek držíme po celou dobu kontroly i případného čtení z DB (Double-checked locking)
    with model_cache_lock:
        if (
            model_cache["adaptive_weights"] is not None
            and (current_time - model_cache["timestamp"]) < MODEL_CACHE_TTL
        ):
            return (
                model_cache["adaptive_weights"],
                model_cache["history_count"],
                model_cache["stats"]
            )

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT vector, history_count FROM model_registry WHERE key='global_brain'"
            )

            row = cursor.fetchone()

            if row is None:
                adaptive_weights = np.zeros(6, dtype=np.float32)
                history_count = 0
            else:
                adaptive_weights = np.array(
                    json.loads(row[0]),
                    dtype=np.float32
                )
                history_count = int(row[1])

            # 🔥 Optimalizace: Načtení všech statistik jedním SQL dotazem namísto tří
            cursor.execute(
                "SELECT key, value FROM stats WHERE key IN ('mean_score', 'score_count', 'score_var')"
            )
            stats_rows = dict(cursor.fetchall())

        stats_payload = {
            "mean_score": float(stats_rows.get("mean_score", 5.0)),
            "score_count": int(stats_rows.get("score_count", 1)),
            "score_var": float(stats_rows.get("score_var", 1.0))
        }

        model_cache.update({
            "timestamp": current_time,
            "adaptive_weights": adaptive_weights,
            "history_count": history_count,
            "stats": stats_payload
        })

    return (
        adaptive_weights,
        history_count,
        stats_payload
    )


def predict_score(features, adaptive_weights, current_stats):
    final_weights = get_final_weights(adaptive_weights)

    # 🔥 základní skóre
    raw_score = np.dot(features, final_weights) * 10

    raw_score = np.clip(raw_score, 1, 10)

    # 🔥 adaptivní drift (rychlejší náběh)
    drift = min(0.4, current_stats["score_count"] / 20000)

    # 🔥 Bezpečné ošetření variance proti dělení nulou
    variance = max(current_stats.get("score_var", 1.0), 1e-6)
    confidence = 1 / (1 + variance)

    adjusted_mean = (
        confidence * current_stats["mean_score"]
        + (1 - confidence) * raw_score
    )

    final_score = (
        (1 - drift) * raw_score
        + drift * adjusted_mean
    )

    return float(np.clip(final_score, 1, 10))

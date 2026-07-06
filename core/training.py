import numpy as np
import json
from fastapi import HTTPException
from db.database import get_db_connection
from core.scoring import invalidate_model_cache, get_final_weights
from config import LEARNING_RATE


def train_centralized_model_transactional(features, ai_score, human_score):
    if features.shape != (6,):
        raise HTTPException(status_code=400, detail="Catastrophic feature length mismatch")
    if not np.isfinite(features).all() or np.any(features < 0) or np.any(features > 1):
        raise HTTPException(status_code=400, detail="Invalid numbers inside face vector bounds")
    if not np.isfinite(ai_score) or not np.isfinite(human_score):
        raise HTTPException(status_code=400, detail="Invalid score")
    if not 0.0 <= ai_score <= 10.0 or not 0.0 <= human_score <= 10.0:
        raise HTTPException(status_code=400, detail="Score out of bounds")

    error = (human_score / 10.0) - (ai_score / 10.0)
    diff_score = abs(human_score - ai_score)
    if diff_score > 4.5:
        error *= 0.05
    elif diff_score > 3.0:
        error *= 0.15

    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE;")
            cursor.execute("SELECT vector, history_count FROM model_registry WHERE key='global_brain'")
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=500, detail="Missing global model")

            adaptive_weights = np.array(json.loads(row[0]), dtype=np.float32)
            current_history = int(row[1])

            cursor.execute("SELECT key, value FROM stats WHERE key IN ('mean_score', 'score_count', 'score_m2', 'score_var')")
            stats = dict(cursor.fetchall())
            if "mean_score" not in stats or "score_count" not in stats:
                raise HTTPException(status_code=500, detail="Stats table corrupted")

            mean = float(stats["mean_score"])
            count = int(float(stats["score_count"]))
            old_m2 = float(stats.get("score_m2", 0.0))

            confidence = max(0.15, min(1.0, current_history / 20.0)) * max(0.15, 1.0 - (current_history / 50000.0))
            adaptive_weights *= 0.9995
            lr = LEARNING_RATE * (1.0 / (1.0 + current_history / 10000.0))

            adaptive_weights += np.clip((lr * error * features * confidence), -0.01, 0.01)
            adaptive_weights = np.clip(adaptive_weights, -0.35, 0.35)
            norm = max(np.sum(np.abs(adaptive_weights)), 1e-6)
            adaptive_weights = adaptive_weights / norm

            cursor.execute("UPDATE model_registry SET vector=?, history_count=? WHERE key='global_brain'", (json.dumps(adaptive_weights.tolist()), current_history + 1))

            new_count = count + 1
            delta = human_score - mean
            new_mean = mean + (delta / new_count)
            delta2 = human_score - new_mean
            new_m2 = old_m2 + (delta * delta2)
            new_variance = max(1e-6, new_m2 / new_count)

            cursor.execute("UPDATE stats SET value=? WHERE key='mean_score'", (float(new_mean),))
            cursor.execute("UPDATE stats SET value=? WHERE key='score_count'", (float(new_count),))
            cursor.execute("INSERT OR REPLACE INTO stats (key, value) VALUES ('score_m2', ?)", (float(new_m2),))
            cursor.execute("INSERT OR REPLACE INTO stats (key, value) VALUES ('score_var', ?)", (float(new_variance),))
            cursor.execute("COMMIT;")
            invalidate_model_cache()
            return get_final_weights(adaptive_weights), new_mean, new_count
        except Exception as e:
            try:
                cursor.execute("ROLLBACK;")
            except Exception:
                pass
            raise e

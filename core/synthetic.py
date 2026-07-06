import json
import random

import numpy as np

from db.database import get_db_connection

DEFAULT_FACE = np.array(
    [0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
    dtype=np.float32
)

def generate_synthetic_face():

    with get_db_connection() as conn:

        cursor = conn.cursor()

        cursor.execute("""
            SELECT MAX(id), MIN(id)
            FROM chaos_db
            WHERE human_score IS NULL
        """)

        row = cursor.fetchone()

        if (
            not row
            or row[0] is None
            or row[1] is None
        ):
            return DEFAULT_FACE.copy()

        max_id = int(row[0])

        min_id = int(row[1])

        random_ids = [
            random.randint(min_id, max_id)
            for _ in range(64)
        ]

        placeholders = ",".join(
            "?" for _ in random_ids
        )

        cursor.execute(f"""
            SELECT features
            FROM chaos_db
            WHERE id IN ({placeholders})
            AND human_score IS NULL
            LIMIT 32
        """, random_ids)

        rows = cursor.fetchall()

    if not rows:
        return DEFAULT_FACE.copy()

    all_features = np.array([
        json.loads(row[0])
        for row in rows
    ], dtype=np.float32)

    base = np.array(
        random.choice(all_features),
        dtype=np.float32
    )

    std = np.clip(

        np.std(
            all_features,
            axis=0
        )

        if len(all_features) > 1
        else np.array(
            [0.05] * 6,
            dtype=np.float32
        ),

        0.02,
        0.10
    )

    synthetic_face = np.clip(
        base + np.random.normal(
            0.0,
            std,
            size=6
        ),
        0.0,
        1.0
    )

    return synthetic_face.astype(
        np.float32
    )
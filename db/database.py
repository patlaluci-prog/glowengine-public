import sqlite3
import json
import numpy as np
import logging
from contextlib import contextmanager
from config import DB_FILE

logger = logging.getLogger("ai_engine")

BASE_WEIGHTS = np.array(
    [0.24, 0.18, 0.16, 0.22, 0.10, 0.10],
    dtype=np.float32
)


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(
        DB_FILE,
        timeout=30.0,
        isolation_level=None,
        check_same_thread=False
    )
    try:
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA cache_size=-64000;")
        conn.execute("PRAGMA mmap_size=268435456;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chaos_db (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    features TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    human_score REAL,
                    votes INTEGER NOT NULL DEFAULT 0,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signature ON chaos_db(signature)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON chaos_db(created_at)")
            
            cursor.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value REAL NOT NULL)")
            cursor.execute("""
                INSERT OR IGNORE INTO stats (key, value)
                VALUES ('mean_score', 5.0), ('score_count', 1.0), ('score_var', 1.0)
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_registry (
                    key TEXT PRIMARY KEY,
                    vector TEXT NOT NULL,
                    history_count INTEGER NOT NULL
                )
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO model_registry (key, vector, history_count)
                VALUES (?, ?, ?)
            """, ("global_brain", json.dumps(BASE_WEIGHTS.tolist()), 0))
            
            cursor.execute("COMMIT;")
            logger.info("Database schemas and seeds initialized successfully.")
        except Exception as e:
            try:
                cursor.execute("ROLLBACK;")
            except Exception:
                logger.exception("Rollback failed during DB init")
            logger.critical(f"Database initialization failed: {e}")
            raise

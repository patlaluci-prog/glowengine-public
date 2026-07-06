import time
import queue
import json
import hashlib
import logging
import threading
import numpy as np
from collections import OrderedDict

from db.database import get_db_connection
from config import (
    MAX_DB_QUEUE,
    MAX_MEMORY_RECORDS,
    MAX_DUPLICATE_CACHE
)

logger = logging.getLogger("ai_engine")

db_write_queue = queue.Queue(maxsize=MAX_DB_QUEUE)
shutdown_event_flag = threading.Event()

duplicate_signature_cache = OrderedDict()
duplicate_cache_lock = threading.RLock()

INSERT_COUNTER = 0
INSERT_COUNTER_LOCK = threading.RLock()


def build_signature(features):
    # Převod na NumPy array pro konzistenci, pokud by ze vstupu přišel list
    feats_arr = np.array(features, dtype=np.float32)
    rounded = np.round(feats_arr, 2)
    return hashlib.sha256(rounded.tobytes()).hexdigest()


def duplicate_cache_exists(signature):
    with duplicate_cache_lock:
        exists = signature in duplicate_signature_cache
        if exists:
            duplicate_signature_cache.move_to_end(signature)
        return exists


def duplicate_cache_add(signature):
    with duplicate_cache_lock:
        duplicate_signature_cache[signature] = time.time()
        duplicate_signature_cache.move_to_end(signature)
        while len(duplicate_signature_cache) > MAX_DUPLICATE_CACHE:
            duplicate_signature_cache.popitem(last=False)


def cleanup_database(cursor):
    # 🔥 OPRAVA DEADLOCKU: Cleanup provádíme nad existujícím cursorem v rámci jedné transakce,
    # neotevíráme nové spojení, které by databázi uzamklo.
    cursor.execute("""
        DELETE FROM chaos_db
        WHERE id NOT IN (
            SELECT id
            FROM chaos_db
            ORDER BY id DESC
            LIMIT ?
        )
    """, (MAX_MEMORY_RECORDS,))


def process_db_task(task):
    global INSERT_COUNTER

    if task.get("type") != "insert":
        return

    features = task["features"]
    human_score = task["human_score"]

    # Zaokrouhlení pro uložení do DB
    optimized_features = np.round(features, 4).tolist()
    
    # 🔥 OPRAVA SIGNATURY: Signaturu generujeme z konzistentních rysů
    signature = build_signature(features)

    votes = 1 if human_score is not None else 0
    confidence = min(1.0, votes / 20.0) if human_score is not None else 0.0

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 🔥 OPRAVA TRANSAKCE: V autocommit režimu (isolation_level=None) řídíme transakce SQL příkazy
        cursor.execute("BEGIN IMMEDIATE;")
        try:
            cursor.execute("""
                INSERT INTO chaos_db
                (features, signature, human_score, votes, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (
                json.dumps(optimized_features),
                signature,
                human_score,
                votes,
                confidence
            ))

            # Kontrola a spuštění čištění databáze pod stejnou transakcí
            should_cleanup = False
            with INSERT_COUNTER_LOCK:
                INSERT_COUNTER += 1
                if INSERT_COUNTER % 500 == 0:
                    should_cleanup = True

            if should_cleanup:
                cleanup_database(cursor)

            cursor.execute("COMMIT;")

        except Exception as e:
            try:
                cursor.execute("ROLLBACK;")
            except Exception:
                pass
            logger.error(f"Async DB Writer crashed: {str(e)}")


def sqlite_writer_worker():
    while not shutdown_event_flag.is_set() or not db_write_queue.empty():
        try:
            task = db_write_queue.get(timeout=1.0)
            try:
                process_db_task(task)
            except Exception as e:
                logger.error(f"DB worker loop exception: {str(e)}")
            finally:
                db_write_queue.task_done()
        except queue.Empty:
            continue
        except Exception as fatal:
            logger.critical(f"FATAL WRITER THREAD FAIL: {str(fatal)}")
            time.sleep(1)


writer_thread = threading.Thread(
    target=sqlite_writer_worker,
    name="AsyncDBWriter",
    daemon=True
)
writer_thread.start()

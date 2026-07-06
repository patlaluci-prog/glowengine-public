import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from security.auth import verify_api_key
from db.database import get_db_connection
from workers.writer import db_write_queue, duplicate_signature_cache, writer_thread
from config import MAX_DB_QUEUE, MODEL_VERSION

router = APIRouter()
logger = logging.getLogger("ai_engine")


def check_db_sync():
    with get_db_connection() as conn:
        conn.execute("SELECT 1;")


@router.get("")
async def health_check(_auth: str = Depends(verify_api_key)):
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, check_db_sync)
        try:
            queue_size = db_write_queue.qsize()
        except (NotImplementedError, AttributeError):
            queue_size = 0

        queue_utilization = round(queue_size / MAX_DB_QUEUE, 3) if MAX_DB_QUEUE > 0 else 0.0

        return {
            "status": "healthy",
            "database": "online",
            "writer_alive": writer_thread.is_alive(),
            "queue_size": queue_size,
            "queue_utilization": queue_utilization,
            "cache_entries": len(duplicate_signature_cache),
            "engine_version": MODEL_VERSION
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Health check failed")
        raise HTTPException(status_code=500, detail="Database unhealthy")

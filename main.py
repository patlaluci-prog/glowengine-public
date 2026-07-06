import logging
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load .env before local imports read configuration.
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import CORS_ALLOW_CREDENTIALS, CORS_ALLOWED_ORIGINS, MODEL_VERSION
from db.database import init_db


logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
)

logger = logging.getLogger("ai_engine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Glow-Up Engine...")
    init_db()
    logger.info(f"Engine version {MODEL_VERSION} initialized")

    yield

    logger.warning("Shutdown initiated. Flushing worker queues...")

    try:
        from core.features import cleanup_thread_local_mesh
        from workers.writer import shutdown_event_flag, writer_thread

        shutdown_event_flag.set()

        if writer_thread.is_alive():
            writer_thread.join(timeout=5)
            if writer_thread.is_alive():
                logger.error("Writer thread failed to stop gracefully")

        cleanup_thread_local_mesh()
        logger.info("Shutdown cleanup completed")
    except Exception:
        logger.exception("Error during shutdown cleanup")


app = FastAPI(
    title="GlowEngine",
    version=MODEL_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(f"Unhandled request crash: {request.method} {request.url.path}")
        raise

    duration = round((time.time() - start_time) * 1000, 2)
    logger.info(f"{request.method} {request.url.path} duration_ms={duration}")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled engine crash caught by middleware")

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "engine_version": MODEL_VERSION,
        },
    )


from api.analyze import router as analyze_router
from api.game import router as game_router
from api.health import router as health_router

app.include_router(analyze_router, prefix="/analyze")
app.include_router(game_router, prefix="/chaos")
app.include_router(health_router, prefix="/health")


@app.get("/")
async def root():
    return {
        "status": "online",
        "engine": "GlowEngine",
        "version": MODEL_VERSION,
    }

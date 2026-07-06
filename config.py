import os
from dotenv import load_dotenv
from fastapi.security import APIKeyHeader

load_dotenv()


def _int_env(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


MODEL_VERSION = "22.1"
LEARNING_RATE = 0.02

DB_FILE = os.getenv("DB_FILE", "engine_data.db")
MAX_MEMORY_RECORDS = 5000
MAX_DB_QUEUE = 10000
MAX_DUPLICATE_CACHE = 25000
MEDIAPIPE_WORKERS = max(1, _int_env("MEDIAPIPE_WORKERS", 2))
MODEL_CACHE_TTL = 3.0

MAX_UPLOAD_SIZE = 5 * 1024 * 1024
MAX_RAW_FILE_SIZE = 5 * 1024 * 1024

MAX_IMAGE_DIMENSION = 6000
MAX_PIXELS = 25_000_000

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 40
MAX_TRACKED_IPS = 10000

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}

API_KEY_NAME = "X-API-Key"
API_KEY = os.getenv("AI_ENGINE_API_KEY")

if not API_KEY:
    raise RuntimeError("AI_ENGINE_API_KEY missing in environment")

CORS_ALLOWED_ORIGINS = [
    item.strip()
    for item in os.getenv("CORS_ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",")
    if item.strip()
]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "0").strip().lower() in {"1", "true", "yes", "on"}

api_key_header = APIKeyHeader(
    name=API_KEY_NAME,
    auto_error=False
)

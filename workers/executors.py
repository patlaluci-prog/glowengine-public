from concurrent.futures import ThreadPoolExecutor

from config import MEDIAPIPE_WORKERS


MEDIAPIPE_EXECUTOR = ThreadPoolExecutor(
    max_workers=MEDIAPIPE_WORKERS,
    thread_name_prefix="mediapipe",
)

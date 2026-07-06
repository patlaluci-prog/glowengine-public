import time
from collections import OrderedDict, deque
from threading import RLock
from fastapi import HTTPException

from config import (
    RATE_LIMIT_MAX_REQUESTS,
    MAX_TRACKED_IPS,
    RATE_LIMIT_WINDOW
)

rate_limit_lock = RLock()
rate_limit_map = OrderedDict()


def cleanup_old_ips(current_time):
    # Předpokládá se volání pod zámkem rate_limit_lock
    expired = [
        ip for ip, timestamps in rate_limit_map.items()
        if not any(current_time - t < RATE_LIMIT_WINDOW for t in timestamps)
    ]
    for ip in expired:
        rate_limit_map.pop(ip, None)


def check_rate_limit(ip_address: str):
    current_time = time.time()

    if not ip_address:
        ip_address = "unknown"

    with rate_limit_lock:
        # =========================
        # CLEANUP (Obrana proti zaplnění RAM)
        # =========================
        if len(rate_limit_map) >= MAX_TRACKED_IPS:
            cleanup_old_ips(current_time)
            
            # Pokud pročištění nestačilo, vyhazujeme nejstarší LRU položky
            while len(rate_limit_map) >= MAX_TRACKED_IPS:
                rate_limit_map.popitem(last=False)

        # =========================
        # INIT & FILTER REQUESTS
        # =========================
        # Pokud IP neznáme, vytvoříme jí prázdnou frontu
        if ip_address not in rate_limit_map:
            rate_limit_map[ip_address] = deque(maxlen=RATE_LIMIT_MAX_REQUESTS)

        # Pročištění historie požadavků dané IP od expirovaných časů
        # Používáme list comprehension, což je v pythonu pro malé fronty výrazně rychlejší
        valid_timestamps = [
            t for t in rate_limit_map[ip_address]
            if current_time - t < RATE_LIMIT_WINDOW
        ]

        # 🔥 OPRAVA LOGIKY: Aktualizujeme stav v mapě a posuneme IP na konec (LRU) 
        # JEŠTĚ PŘEDTÍM, než vyhodíme výjimku. Tím zajistíme konzistenci dat.
        updated_queue = deque(valid_timestamps, maxlen=RATE_LIMIT_MAX_REQUESTS)
        rate_limit_map[ip_address] = updated_queue
        rate_limit_map.move_to_end(ip_address)

        # =========================
        # EVALUATE RATE LIMIT
        # =========================
        if len(updated_queue) >= RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )

        # Pokud limit nepřeteče, zapíšeme aktuální pokus do fronty
        updated_queue.append(current_time)

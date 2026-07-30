import threading
import time


_LOCK = threading.Lock()
_IN_FLIGHT = {}
_TTL_SECONDS = 20


def _cleanup_expired(now):
    expired = [key for key, ts in _IN_FLIGHT.items() if now - ts > _TTL_SECONDS]
    for key in expired:
        _IN_FLIGHT.pop(key, None)


def acquire_key(key):
    now = time.time()
    with _LOCK:
        _cleanup_expired(now)
        if key in _IN_FLIGHT:
            return False
        _IN_FLIGHT[key] = now
        return True


def release_key(key):
    with _LOCK:
        _IN_FLIGHT.pop(key, None)

import threading
import time


class SimpleRateLimiter:
    def __init__(self, min_interval_seconds: float):
        interval = float(min_interval_seconds)
        if interval < 0:
            raise ValueError("min_interval_seconds must be >= 0")
        self._min_interval_seconds = interval
        self._lock = threading.Lock()
        self._next_allowed_at = 0.0

    def wait(self):
        sleep_seconds = 0.0
        with self._lock:
            now = time.monotonic()
            allowed_at = max(self._next_allowed_at, now)
            sleep_seconds = allowed_at - now
            self._next_allowed_at = allowed_at + self._min_interval_seconds

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
        return sleep_seconds


joongna_search_limiter = SimpleRateLimiter(min_interval_seconds=1.0)
joongna_detail_limiter = SimpleRateLimiter(min_interval_seconds=0.5)


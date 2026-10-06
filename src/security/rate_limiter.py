import time
from collections import defaultdict, deque
from threading import Lock

class RateLimiter:
    """Thread-safe in-memory rate limiter."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be greater than zero.")

        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero.")

        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        """Return whether a request is allowed for the given key."""
        now = time.monotonic()
        window_start = now - self.window_seconds

        with self._lock:
            timestamps = self._requests[key]

            while timestamps and timestamps[0] <= window_start:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                return False

            timestamps.append(now)
            return True
"""Simple in-memory sliding window rate limiter utilities."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict


class RateLimitExceeded(Exception):
    """Raised when a rate limit has been exceeded."""

    def __init__(self, retry_after: float | None = None):
        super().__init__("Rate limit exceeded")
        self.retry_after = retry_after


@dataclass
class _WindowConfig:
    limit: int
    window_seconds: int


class SlidingWindowRateLimiter:
    """Track request counts within a sliding time window."""

    def __init__(self, *, limit: int, window_seconds: int):
        self._config = _WindowConfig(limit=limit, window_seconds=window_seconds)
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.RLock()

    def _prune(self, key: str, now: float) -> None:
        window = self._config.window_seconds
        dq = self._events[key]
        while dq and now - dq[0] > window:
            dq.popleft()
        if not dq:
            # Keep the dict tidy to avoid unbounded growth
            self._events.pop(key, None)

    def hit(self, key: str) -> None:
        now = time.time()
        with self._lock:
            dq = self._events[key]
            self._prune(key, now)
            if len(dq) >= self._config.limit:
                retry_after = max(0.0, dq[0] + self._config.window_seconds - now)
                raise RateLimitExceeded(retry_after=retry_after)
            dq.append(now)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


class PasswordResetRateLimiter:
    """Composite limiter that enforces multiple password reset limits."""

    def __init__(self) -> None:
        # Tune these defaults as needed; they are intentionally conservative.
        self._per_email = SlidingWindowRateLimiter(limit=5, window_seconds=3600)
        self._per_ip = SlidingWindowRateLimiter(limit=20, window_seconds=3600)
        self._per_pair = SlidingWindowRateLimiter(limit=5, window_seconds=3600)

    def check(self, *, email: str, ip_address: str | None) -> None:
        key_email = f"email:{email.lower()}"
        key_ip = f"ip:{(ip_address or 'unknown')}"
        key_pair = f"pair:{ip_address or 'unknown'}:{email.lower()}"

        self._per_email.hit(key_email)
        self._per_ip.hit(key_ip)
        self._per_pair.hit(key_pair)

    def reset(self) -> None:
        self._per_email.reset()
        self._per_ip.reset()
        self._per_pair.reset()


PASSWORD_RESET_RATE_LIMITER = PasswordResetRateLimiter()

__all__ = [
    "RateLimitExceeded",
    "SlidingWindowRateLimiter",
    "PasswordResetRateLimiter",
    "PASSWORD_RESET_RATE_LIMITER",
]

from collections import deque

from app.utils.rate_limiter import SlidingWindowRateLimiter


def test_prune_removes_empty_key_from_internal_store():
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=10)
    limiter._events["email:test@example.com"] = deque([1.0])

    limiter._prune("email:test@example.com", now=20.0)

    assert "email:test@example.com" not in limiter._events

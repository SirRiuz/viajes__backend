"""
Fixed-window rate limits on the shared cache (Valkey in production, so the
count is the same for every worker and process).
"""

from django.core.cache import cache


def hit(key: str, limit: int, window_s: int) -> bool:
    """
    Counts one attempt on ``key``. True while it is within ``limit`` per
    window; False once over it. Atomic: add() opens the window, incr() counts
    (no read-then-write race letting extra attempts through).
    """
    key = f"rl:{key}"
    if cache.add(key, 1, window_s):
        return True
    try:
        return cache.incr(key) <= limit
    except ValueError:  # expired between add() and incr()
        cache.add(key, 1, window_s)
        return True


def blocked(key: str, limit: int) -> bool:
    """Whether ``key`` already used its attempts (without counting one)."""
    return (cache.get(f"rl:{key}") or 0) >= limit


def reset(key: str) -> None:
    cache.delete(f"rl:{key}")

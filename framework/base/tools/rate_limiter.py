from __future__ import annotations

from dataclasses import dataclass

from mm_toolbox.time import time_s


@dataclass
class RateLimiter:
    """Simple token-bucket rate limiter.

    Tokens refill at "rate_per_sec" up to "capacity". Use try_acquire() to
    attempt consuming tokens, and time_to_availability() to learn how long to
    wait until the requested tokens are available.
    """

    rate_per_sec: int
    capacity: int

    def __post_init__(self) -> None:
        if self.rate_per_sec <= 0:
            raise ValueError("rate_per_sec must be > 0")
        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")

        self._tokens: int = self.capacity
        self._last_refill_s: float = float(time_s())

    def _refill(self) -> None:
        now_s: float = float(time_s())
        elapsed: float = max(0.0, now_s - self._last_refill_s)
        if elapsed > 0.0:
            added_tokens: int = int(elapsed * self.rate_per_sec)
            self._tokens = min(self.capacity, self._tokens + added_tokens)
            self._last_refill_s = now_s

    def try_acquire(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens without blocking.

        Returns True if tokens were consumed, False otherwise.
        """
        if tokens <= 0:
            return True
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    def time_to_availability(self, tokens: int = 1) -> float:
        """Seconds until the requested tokens are available (0 if already available)."""
        if tokens <= 0:
            return 0.0
        self._refill()
        deficit: float = max(0.0, tokens - self._tokens)
        if deficit == 0.0:
            return 0.0
        return deficit / self.rate_per_sec

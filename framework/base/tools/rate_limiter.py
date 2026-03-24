"""Token-bucket rate limiting utilities used by exchange clients.

The module exposes `RateLimiter`, a small stateful helper that:
- refills tokens at a fixed rate
- enforces a maximum token capacity
- provides non-blocking acquisition and wait-time estimation methods
"""

from __future__ import annotations

from mm_toolbox.time import time_s


class RateLimiter:
    """Token-bucket rate limiter with bounded capacity.

    Tokens refill at `rate_per_sec` up to `capacity`. Use `try_acquire()` to
    attempt consuming tokens, and `time_to_availability()` to estimate how long
    to wait until enough tokens are available.
    """

    def __init__(self, rate_per_sec: int, capacity: int) -> None:
        """Initialize limiter state and validate configuration.

        Args:
            rate_per_sec: Number of whole tokens added to the bucket each second.
            capacity: Maximum number of tokens that can be stored.

        Raises:
            ValueError: If `rate_per_sec` or `capacity` is not greater than zero.
        """
        if rate_per_sec <= 0:
            raise ValueError("rate_per_sec must be > 0")
        if capacity <= 0:
            raise ValueError("capacity must be > 0")

        self.rate_per_sec: int = rate_per_sec
        self.capacity: int = capacity
        self._tokens: int = capacity
        self._last_refill_s: float = float(time_s())

    def _refill(self) -> None:
        """Refill tokens based on elapsed wall-clock time.

        The refill operation is integer-based and saturates at `capacity`.
        """
        now_s: float = float(time_s())
        elapsed: float = max(0.0, now_s - self._last_refill_s)
        if elapsed > 0.0:
            added_tokens: int = int(elapsed * self.rate_per_sec)
            self._tokens = min(self.capacity, self._tokens + added_tokens)
            self._last_refill_s = now_s

    def try_acquire(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens without blocking.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            True if enough tokens were available and consumed, otherwise False.
        """
        if tokens <= 0:
            return True
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    def time_to_availability(self, tokens: int = 1) -> float:
        """Compute the wait time before a token request can be served.

        Args:
            tokens: Number of tokens requested.

        Returns:
            Seconds until enough tokens are available, or `0.0` if already available.
        """
        if tokens <= 0:
            return 0.0
        self._refill()
        deficit: float = max(0.0, tokens - self._tokens)
        if deficit == 0.0:
            return 0.0
        return deficit / self.rate_per_sec

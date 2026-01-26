"""Tests for framework.base.tools.rate_limiter module.

Tests cover:
- RateLimiter token bucket algorithm with rate and capacity
- Token acquisition and exhaustion
- Time-based token refilling and capacity saturation
- Time to availability calculations
- Edge cases with zero/negative tokens and fractional tokens

Tests are organized by dependency layer:
1. Primitives: RateLimiter basic operations and token management
2. Edge cases: Invalid inputs, zero/negative tokens, fractional tokens
"""

from __future__ import annotations

import pytest

from framework.base.tools.rate_limiter import RateLimiter


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture()
def clock(monkeypatch):
    """Mock time clock for testing rate limiter."""

    class _Clock:
        def __init__(self) -> None:
            self._t: int = 0

        def set(self, t: int) -> None:
            self._t = int(t)

        def advance(self, dt: int) -> None:
            self._t += int(dt)

        def time_s(self) -> int:
            return int(self._t)

    c = _Clock()
    monkeypatch.setattr("framework.base.tools.rate_limiter.time_s", c.time_s)
    return c


# =============================================================================
# =============================================================================


class TestRateLimiter:
    """Test RateLimiter basic token acquisition and refilling."""

    def test_simple_acquire_and_exhaustion(self, clock):
        """Test acquiring tokens until exhaustion."""
        clock.set(100)
        rl = RateLimiter(rate_per_sec=1.0, capacity=3.0)

        assert rl.try_acquire(1.0) is True
        assert rl.try_acquire(2.0) is True
        # Exhausted, no time advanced
        assert rl.try_acquire(1.0) is False

    def test_refill_over_time(self, clock):
        """Test tokens refill at specified rate over time."""
        clock.set(0)
        rl = RateLimiter(rate_per_sec=2.0, capacity=5.0)

        # Drain all tokens
        assert rl.try_acquire(5.0) is True
        assert rl.try_acquire(1.0) is False

        # After 1s, 2 tokens should be available
        clock.advance(1)
        assert rl.try_acquire(2.0) is True
        # Still at the same second, no more tokens
        assert rl.try_acquire(1.0) is False

    def test_capacity_saturation(self, clock):
        """Test tokens are capped at capacity even with long time."""
        clock.set(0)
        rl = RateLimiter(rate_per_sec=2.0, capacity=5.0)

        # Drain all tokens
        assert rl.try_acquire(5.0) is True

        # After 1s, acquire 2 tokens
        clock.advance(1)
        assert rl.try_acquire(2.0) is True

        # Advance to fully saturate back to capacity (last refill was at t=1)
        clock.advance(3)  # now t=4 -> 3s * 2 = 6, capped at capacity 5
        assert rl.try_acquire(5.0) is True
        assert rl.try_acquire(1.0) is False

    def test_time_to_availability_when_drained(self, clock):
        """Test time_to_availability calculates correct wait time."""
        clock.set(0)
        rl = RateLimiter(rate_per_sec=2.0, capacity=3.0)

        # Drain
        assert rl.try_acquire(3.0) is True

        # No time advanced: need 0.5s for 1 token, 1.0s for 2 tokens
        assert rl.time_to_availability(1.0) == pytest.approx(0.5)
        assert rl.time_to_availability(2.0) == pytest.approx(1.0)

    def test_time_to_availability_with_partial_tokens(self, clock):
        """Test time_to_availability when some tokens are available."""
        clock.set(0)
        rl = RateLimiter(rate_per_sec=2.0, capacity=3.0)

        # Drain
        assert rl.try_acquire(3.0) is True

        # Advance 1s -> 2 tokens available now
        clock.advance(1)
        assert rl.time_to_availability(2.0) == pytest.approx(0.0)
        # Requesting more than available should report remaining divided by rate
        # At t=1, tokens are 2. Asking for 3 -> deficit 1 -> 0.5s
        assert rl.time_to_availability(3.0) == pytest.approx(0.5)


# =============================================================================
# =============================================================================


class TestRateLimiterEdgeCases:
    """Test RateLimiter edge cases and boundary conditions."""

    @pytest.mark.parametrize(
        "rate,cap",
        [
            (0.0, 1.0),
            (-1.0, 1.0),
            (1.0, 0.0),
            (1.0, -5.0),
        ],
    )
    def test_invalid_initialization_raises(self, rate: float, cap: float):
        """Test RateLimiter raises ValueError for invalid rate/capacity."""
        with pytest.raises(ValueError):
            RateLimiter(rate_per_sec=rate, capacity=cap)

    def test_zero_and_negative_token_requests(self, clock):
        """Test zero and negative token requests are treated as immediate success."""
        clock.set(10)
        rl = RateLimiter(rate_per_sec=1.0, capacity=1.0)

        # Drain
        assert rl.try_acquire(1.0) is True
        # Zero/negative requests are treated as immediate success / zero wait
        assert rl.try_acquire(0.0) is True
        assert rl.try_acquire(-1.0) is True
        assert rl.time_to_availability(0.0) == pytest.approx(0.0)
        assert rl.time_to_availability(-2.0) == pytest.approx(0.0)

    def test_fractional_tokens(self, clock):
        """Test RateLimiter handles fractional tokens correctly."""
        clock.set(0)
        rl = RateLimiter(rate_per_sec=1.5, capacity=3.0)

        assert rl.try_acquire(1.5) is True  # remaining 1.5
        assert rl.try_acquire(2.0) is False  # not enough

        # After 1s, +1.5 tokens -> total 3.0 capped
        clock.advance(1)
        assert rl.try_acquire(3.0) is True

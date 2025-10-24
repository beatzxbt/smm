import pytest

from framework.base.tools.rate_limiter import RateLimiter


@pytest.fixture()
def clock(monkeypatch):
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


@pytest.mark.parametrize(
    "rate,cap",
    [
        (0.0, 1.0),
        (-1.0, 1.0),
        (1.0, 0.0),
        (1.0, -5.0),
    ],
)
def test_invalid_initialization(rate: float, cap: float):
    with pytest.raises(ValueError):
        RateLimiter(rate_per_sec=rate, capacity=cap)


def test_simple_acquire_and_exhaustion(clock):
    clock.set(100)
    rl = RateLimiter(rate_per_sec=1.0, capacity=3.0)

    assert rl.try_acquire(1.0) is True
    assert rl.try_acquire(2.0) is True
    # Exhausted, no time advanced
    assert rl.try_acquire(1.0) is False


def test_refill_over_time_and_capacity_saturation(clock):
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

    # Advance to fully saturate back to capacity (last refill was at t=1)
    clock.advance(3)  # now t=4 -> 3s * 2 = 6, capped at capacity 5
    assert rl.try_acquire(5.0) is True
    assert rl.try_acquire(1.0) is False


def test_time_to_availability(clock):
    clock.set(0)
    rl = RateLimiter(rate_per_sec=2.0, capacity=3.0)

    # Drain
    assert rl.try_acquire(3.0) is True

    # No time advanced: need 0.5s for 1 token, 1.0s for 2 tokens
    assert rl.time_to_availability(1.0) == pytest.approx(0.5)
    assert rl.time_to_availability(2.0) == pytest.approx(1.0)

    # Advance 1s -> 2 tokens available now
    clock.advance(1)
    assert rl.time_to_availability(2.0) == pytest.approx(0.0)
    # Requesting more than available should report remaining divided by rate
    # At t=1, tokens are 2. Asking for 3 -> deficit 1 -> 0.5s
    assert rl.time_to_availability(3.0) == pytest.approx(0.5)


def test_zero_and_negative_token_requests(clock):
    clock.set(10)
    rl = RateLimiter(rate_per_sec=1.0, capacity=1.0)

    # Drain
    assert rl.try_acquire(1.0) is True
    # Zero/negative requests are treated as immediate success / zero wait
    assert rl.try_acquire(0.0) is True
    assert rl.try_acquire(-1.0) is True
    assert rl.time_to_availability(0.0) == pytest.approx(0.0)
    assert rl.time_to_availability(-2.0) == pytest.approx(0.0)


def test_fractional_tokens(clock):
    clock.set(0)
    rl = RateLimiter(rate_per_sec=1.5, capacity=3.0)

    assert rl.try_acquire(1.5) is True  # remaining 1.5
    assert rl.try_acquire(2.0) is False  # not enough

    # After 1s, +1.5 tokens -> total 3.0 capped
    clock.advance(1)
    assert rl.try_acquire(3.0) is True


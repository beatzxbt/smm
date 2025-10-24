import pytest

from framework.base.tools.moving_average import ExponentialMovingAverage


def test_ema_with_period_initialization_and_updates():
    ema = ExponentialMovingAverage(period=9)
    assert ema.get_value() is None

    first = ema.update(10.0)
    assert first == 10.0
    assert ema.get_value() == 10.0

    second = ema.update(12.0)
    assert isinstance(second, float)
    assert second > 10.0
    assert second < 12.0


def test_ema_with_alpha_initialization():
    ema = ExponentialMovingAverage(alpha=0.5)
    assert ema.update(10.0) == 10.0
    assert ema.update(12.0) == 11.0


def test_ema_reset():
    ema = ExponentialMovingAverage(alpha=0.5)
    ema.update(10.0)
    ema.reset()
    assert ema.get_value() is None
    assert ema.update(8.0) == 8.0


@pytest.mark.parametrize("period,alpha", [(0, None), (None, 0.0), (None, None)])
def test_ema_invalid_init(period, alpha):
    with pytest.raises(ValueError):
        ExponentialMovingAverage(period=period, alpha=alpha)

import numpy as np
import pytest

from framework.base.tools.rounder import Rounder, RounderConfig


def test_rounder_basic_price_size_rounding():
    r = Rounder(tick_size=0.5, lot_size=0.1)
    assert r.bid_price(100.74) == 100.5
    assert r.ask_price(100.26) == 100.5
    assert r.size(0.26) == 0.2


def test_rounder_config_variations():
    cfg = RounderConfig(
        round_bids_down=False, round_asks_up=False, round_sizes_up=False
    )
    r = Rounder(tick_size=1.0, lot_size=2.0, config=cfg)
    assert r.bid_price(100.1) == 101.0
    assert r.ask_price(100.9) == 100.0
    assert r.size(5.1) == 6.0


def test_rounder_array_rounding():
    r = Rounder(tick_size=0.25, lot_size=0.5)
    prices = np.array([100.01, 100.24, 100.25, 100.49, 100.50, 100.74])
    sizes = np.array([0.1, 0.49, 0.5, 0.74, 1.0])

    bids = r.bid_prices(prices)
    asks = r.ask_prices(prices)
    rsizes = r.sizes(sizes)

    assert np.allclose(bids, np.array([100.0, 100.0, 100.25, 100.25, 100.5, 100.5]))
    assert np.allclose(asks, np.array([100.25, 100.25, 100.25, 100.5, 100.5, 100.75]))
    assert np.allclose(rsizes, np.array([0.0, 0.5, 0.5, 0.5, 1.0]))


@pytest.mark.parametrize("tick_size,lot_size", [(0.0, 1.0), (1.0, 0.0), (-1.0, 1.0)])
def test_rounder_invalid_init(tick_size, lot_size):
    with pytest.raises(ValueError):
        Rounder(tick_size=tick_size, lot_size=lot_size)

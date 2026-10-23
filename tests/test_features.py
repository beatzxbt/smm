import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pytest
from src.strategy.features.mark_spread import log_price_difference
from src.strategy.features.ob_imbalance import orderbook_imbalance

class TestMarkSpread:
    def test_log_price_difference_positive(self):
        # When follow > base, logarithmic difference should be positive
        follow = 49000.0
        base = 48980.0
        result = log_price_difference(follow=follow, base=base)
        expected = np.log(follow / base) * 100
        assert result > 0
        assert pytest.approx(result, rel=1e-7) == expected
        assert pytest.approx(result, rel=1e-7) == 0.04082465866049452

    def test_log_price_difference_negative(self):
        # When follow < base, logarithmic difference should be negative
        follow = 48980.0
        base = 49000.0
        result = log_price_difference(follow=follow, base=base)
        expected = np.log(follow / base) * 100
        assert result < 0
        assert pytest.approx(result, rel=1e-7) == expected
        assert pytest.approx(result, rel=1e-7) == -0.04082465866049452

    def test_log_price_difference_equal(self):
        assert log_price_difference(follow=50000.0, base=50000.0) == 0.0


class TestOrderbookImbalance:
    def test_orderbook_imbalance_docstring_example(self):
        bids = np.array([
            [100.00, 0.35194],
            [99.75, 0.16040],
            [99.50, 0.46248],
            [99.25, 0.79625],
            [99.00, 0.19408],
        ])
        asks = np.array([
            [101.00, 0.80763],
            [101.25, 0.30421],
            [101.50, 0.04038],
            [101.75, 0.39473],
            [102.00, 0.97438],
        ])
        depths = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        result = orderbook_imbalance(bids, asks, depths)
        assert pytest.approx(result, rel=1e-7) == -0.7734791082203096

    def test_orderbook_imbalance_symmetric(self):
        # Symmetric order book around mid price should yield 0 imbalance
        bids = np.array([
            [100.0, 1.0],
            [99.0, 2.0],
            [98.0, 3.0],
        ])
        asks = np.array([
            [100.0, 1.0],
            [101.0, 2.0],
            [102.0, 3.0],
        ])
        depths = np.array([50.0, 100.0, 200.0])
        result = orderbook_imbalance(bids, asks, depths)
        assert pytest.approx(result, abs=1e-9) == 0.0

    def test_orderbook_imbalance_bps_depth_scaling(self):
        # Verify that depths in basis points (bps) correctly filter book levels:
        # Best bid = 100.0, best ask = 100.0
        # Second bid = 99.0 (100 bps away: 100 * (1 - 0.01))
        # Second ask = 101.0 (100 bps away: 100 * (1 + 0.01))
        bids = np.array([
            [100.0, 1.0],
            [99.0, 5.0],
        ])
        asks = np.array([
            [100.0, 2.0],
            [101.0, 1.0],
        ])
        # At 50 bps depth (0.005), 99.0 and 101.0 should be excluded:
        # min_bid = 99.5, max_ask = 100.5 -> bid size = 1.0, ask size = 2.0
        # Imbalance = log(1.0 / 2.0) = -log(2) < 0
        depth_narrow = np.array([50.0])
        result_narrow = orderbook_imbalance(bids, asks, depth_narrow)
        expected_narrow = np.log(1.0 / 2.0) * 1.5  # ema_weights(1) has alpha=3/2=1.5
        assert pytest.approx(result_narrow, rel=1e-7) == expected_narrow
        assert result_narrow < 0

        # At 150 bps depth (0.015), 99.0 and 101.0 should be included:
        # min_bid = 98.5, max_ask = 101.5 -> bid size = 6.0, ask size = 3.0
        # Imbalance = log(6.0 / 3.0) = log(2) > 0
        depth_wide = np.array([150.0])
        result_wide = orderbook_imbalance(bids, asks, depth_wide)
        expected_wide = np.log(6.0 / 3.0) * 1.5
        assert pytest.approx(result_wide, rel=1e-7) == expected_wide
        assert result_wide > 0

from framework.tools import Orderbook
from smm.features.base_feature import BaseFeature

class OrderbookImbalance(BaseFeature):
    """Calculates the imbalance between bid and ask liquidity within a specified price range.
    
    This feature measures the ratio of cumulative bid size to cumulative ask size
    within a configurable price range around the mid price. The price range is defined
    as a percentage (in basis points) of the mid price.
    
    A value greater than 1.0 indicates more buying pressure (more bid liquidity),
    while a value less than 1.0 indicates more selling pressure (more ask liquidity).
    A value of exactly 1.0 represents a perfectly balanced orderbook.
    
    The feature can be used to:
    1. Predict short-term price movements (higher bid liquidity may lead to price increases)
    2. Identify potential support/resistance levels
    3. Gauge market sentiment and order flow imbalances
    
    Args:
        depth_bps (float): Depth in basis points (1bp = 0.01%) to consider around the mid price.
                          Default is 100.0 (1%).
    """
    def __init__(self, depth_bps: float=100.0):
        super().__init__()

        self._depth_decimal = depth_bps / 10_000.0
        
    def update(self, orderbook: Orderbook) -> float:
        bids = orderbook.get_bids()
        asks = orderbook.get_asks()
        mid_px = orderbook.get_mid_px()

        max_bid = mid_px - (mid_px * self._depth_decimal)
        max_ask = mid_px + (mid_px * self._depth_decimal)
        bid_cum_size = bids[bids[:, 0] >= max_bid][:, 1].sum()
        ask_cum_size = asks[asks[:, 0] <= max_ask][:, 1].sum()

        self._value = bid_cum_size / ask_cum_size
        return self._value
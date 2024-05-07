import numpy as np
from typing import Tuple, Dict, Union

from smm.sharedstate import SmmSharedState
from smm.features.trades_diff import trades_diffs
from smm.features.trades_imbalance import trades_imbalance
from smm.features.orderbook_imbalance import orderbook_imbalance

class FeatureEngine:
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss

        self.fair_price_pred = {
            "wmid":         0.10,
            "tight_vamp":   0.10,
            "mid_vamp":     0.15,
            "deep_vamp":    0.15,
            "book_imb":     0.25,
            "trades_imb":   0.25
        }

        self.volatility_pred = {
            "trades_diffs": 1.0
        }
        
    def wmid_imbalance(self) -> float:
        return (self.ss.orderbook.get_wmid() / self.ss.orderbook.get_mid())

    def tight_vamp_imbalance(self) -> float:
        dollars_to_size = 25_000 / self.ss.orderbook.get_mid()
        return (self.ss.orderbook.get_vamp(dollars_to_size) / self.ss.orderbook.get_mid())

    def mid_vamp_imbalance(self) -> float:
        dollars_to_size = 75_000 / self.ss.orderbook.get_mid()
        return (self.ss.orderbook.get_vamp(dollars_to_size) / self.ss.orderbook.get_mid())
    
    def deep_vamp_imbalance(self) -> float:
        dollars_to_size = 200_000 / self.ss.orderbook.get_mid()
        return (self.ss.orderbook.get_vamp(dollars_to_size) / self.ss.orderbook.get_mid())
    
    def orderbook_imbalance(self) -> float:
        return orderbook_imbalance(
            bids=self.ss.orderbook.bids,
            asks=self.ss.orderbook.asks,
            depths=np.array([10.0, 25.0, 50.0, 100.0, 250.0])
        )
    
    def trades_imbalance(self) -> float:
        return trades_imbalance(
            trades=self.ss.trades,
            window=100
        )
    
    def trades_differences(self) -> float:
        return trades_diffs(
            trades=self.ss.trades,
            lookback=100
        )

    def generate_skew(self) -> float:
        skew = 0.0
        skew += self.wmid_imbalance() * self.weights["wmid"]
        skew += self.tight_vamp_imbalance() * self.weights["tight_vamp"]
        skew += self.mid_vamp_imbalance() * self.weights["mid_vamp"]
        skew += self.deep_vamp_imbalance() * self.weights["deep_vamp"]
        skew += self.orderbook_imbalance() * self.weights["book_imb"]
        skew += self.trades_imbalance() * self.weights["trades_imb"]
        return skew
    
    def generate_vol(self) -> float:
        vol = 0.0
        vol += self.trades_differences() * self.volatility_pred["trades_diffs"]
        return vol
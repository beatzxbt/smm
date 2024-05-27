import numpy as np

from smm.sharedstate import SmmSharedState
from smm.features.trades_diff import trades_diffs
from smm.features.trades_imbalance import trades_imbalance
from smm.features.orderbook_imbalance import orderbook_imbalance


class FeatureEngine:
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss

        self.fair_price_pred = {
            "wmid": 0.10,
            "tight_vamp": 0.10,
            "mid_vamp": 0.15,
            "deep_vamp": 0.15,
            "book_imb": 0.25,
            "trades_imb": 0.25,
        }

        self.volatility_pred = {"trades_diffs": 1.0}

    def wmid_imbalance(self) -> float:
        return self.ss.data["orderbook"].get_wmid() / self.ss.data["orderbook"].get_mid()

    def vamp_imbalance(self, depth: int) -> float:
        dollars_to_size = depth / self.ss.data["orderbook"].get_mid()
        return self.ss.data["orderbook"].get_vamp(dollars_to_size) / self.ss.data["orderbook"].get_mid()

    def orderbook_imbalance(self) -> float:
        return orderbook_imbalance(
            bids=self.ss.data["orderbook"].bids,
            asks=self.ss.data["orderbook"].asks,
            depths=np.array([10.0, 25.0, 50.0, 100.0, 250.0]),
        )

    def trades_imbalance(self) -> float:
        return trades_imbalance(trades=self.ss.data["trades"]._unwrap(), window=100)

    def trades_differences(self) -> float:
        return trades_diffs(trades=self.ss.data["trades"]._unwrap(), lookback=100)

    def generate_skew(self) -> float:
        skew = 0.0
        skew += self.wmid_imbalance() * self.fair_price_pred["wmid"]
        skew += self.vamp_imbalance(depth=25000) * self.fair_price_pred["tight_vamp"]
        skew += self.vamp_imbalance(depth=75000) * self.fair_price_pred["mid_vamp"]
        skew += self.vamp_imbalance(depth=200000) * self.fair_price_pred["deep_vamp"]
        skew += self.orderbook_imbalance() * self.fair_price_pred["book_imb"]
        skew += self.trades_imbalance() * self.fair_price_pred["trades_imb"]
        return skew

    def generate_vol(self) -> float:
        vol = 0.0
        vol += self.trades_differences() * self.volatility_pred["trades_diffs"]
        return vol

import numpy as np
from src.strategy.features.momentum import momentum_v1
from src.strategy.features.mark_spread import log_price_difference
from src.strategy.features.bba_imbalance import bba_imbalance
from src.sharedstate import SharedState

class Features:
    """
    WARNING: Some features are disabled for Bybit-only streams    
    """
    depths = np.array([200, 100, 50, 25, 10])

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss

    def bybit_mark_wmid_spread(self) -> float:
        return log_price_difference(
            p1=self.ss.bybit_mark_price, 
            p2=self.ss.bybit_wmid
        )

    def binance_bybit_wmid_spread(self) -> float:
        return log_price_difference(
            p1=self.ss.binance_wmid, 
            p2=self.ss.bybit_wmid
        )

    def bybit_bba_imbalance(self) -> float:
        return bba_imbalance(
            bid=self.ss.bybit_bba[0][1], 
            ask=self.ss.bybit_bba[1][1]
        )
    
    def binance_bba_imbalance(self) -> float:
        return bba_imbalance(
            bid=self.ss.binance_bba[0][1], 
            ask=self.ss.binance_bba[1][1]
        )
    
    def bybit_wmid_vamp_spread(self) -> float:
        return log_price_difference(
            p1=self.ss.bybit_vamp, 
            p2=self.ss.bybit_wmid
        )

    def binance_wmid_vamp_spread(self) -> float:
        return log_price_difference(
            p1=self.ss.binance_vamp, 
            p2=self.ss.binance_wmid
        )

    def generate_skew(self) -> float:
        total_skew = 0

        if self.ss.primary_data_feed == "BINANCE":
            total_skew += self.bybit_mark_wmid_spread() * 0.2
            total_skew += self.binance_bybit_wmid_spread() * 0.1
            total_skew += self.bybit_bba_imbalance() * 0.1
            total_skew += self.binance_bba_imbalance() * 0.2
            total_skew += self.bybit_wmid_vamp_spread() * 0.2
            total_skew += self.binance_wmid_vamp_spread() * 0.2

        else:
            total_skew += self.bybit_mark_wmid_spread() * 0.4
            total_skew += self.bybit_bba_imbalance() * 0.2
            total_skew += self.bybit_wmid_vamp_spread() * 0.4

        return total_skew
import numpy as np
from src.strategy.features.mark_spread import log_price_difference
from src.strategy.features.bba_imbalance import bba_imbalance
from src.strategy.features.ob_imbalance import orderbook_imbalance
from src.strategy.features.trades_imbalance import trades_imbalance
from src.sharedstate import SharedState

class Features:
    """
    WARNING: Some features are disabled for Bybit-only streams    
    """
    _orderbook_depths_ = np.array([10, 25, 50, 100, 200, 500], dtype=np.int64)
    _trades_window_ = 1000

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss

    def bybit_mark_wmid_spread(self) -> float:
        return log_price_difference(
            follow=self.ss.bybit_mark_price, 
            base=self.ss.bybit_wmid
        )

    def binance_bybit_wmid_spread(self) -> float:
        return log_price_difference(
            follow=self.ss.binance_wmid, 
            base=self.ss.bybit_wmid
        )

    def bybit_bba_imbalance(self) -> float:
        return bba_imbalance(
            bba=self.ss.bybit_bba
        )
    
    def binance_bba_imbalance(self) -> float:
        return bba_imbalance(
            bba=self.ss.binance_bba
        )
    
    def bybit_wmid_vamp_spread(self) -> float:
        return log_price_difference(
            follow=self.ss.bybit_vamp, 
            base=self.ss.bybit_wmid
        )

    def binance_wmid_vamp_spread(self) -> float:
        return log_price_difference(
            follow=self.ss.binance_vamp, 
            base=self.ss.binance_wmid
        )
    
    def bybit_orderbook_imbalance(self) -> float:
        return orderbook_imbalance(
            bids=self.ss.bybit_book.bids,
            asks=self.ss.bybit_book.asks,
            depths=self._orderbook_depths_
        )

    def binance_orderbook_imbalance(self) -> float:
        return orderbook_imbalance(
            bids=self.ss.binance_book.bids,
            asks=self.ss.binance_book.asks,
            depths=self._orderbook_depths_
        )
    
    def bybit_trades_imbalance(self) -> float:
        return trades_imbalance(
            trades=self.ss.bybit_trades._unwrap(), 
            window=self._trades_window_
        )

    def binance_trades_imbalance(self) -> float:
        return trades_imbalance(
            trades=self.ss.binance_trades._unwrap(), 
            window=self._trades_window_
        )

    def generate_skew(self) -> float:
        total_skew = 0

        if self.ss.primary_data_feed == "BINANCE":
            # Total weight = 0.4
            total_skew += self.bybit_bba_imbalance() * 0.025
            total_skew += self.binance_bba_imbalance() * 0.025
            total_skew += self.bybit_mark_wmid_spread() * 0.075
            total_skew += self.binance_bybit_wmid_spread() * 0.075
            total_skew += self.bybit_wmid_vamp_spread() * 0.075
            total_skew += self.binance_wmid_vamp_spread() * 0.075

            # Total weight = 0.6
            total_skew += self.binance_orderbook_imbalance() * 0.2
            total_skew += self.binance_trades_imbalance() * 0.2
            total_skew += self.bybit_orderbook_imbalance() * 0.1
            total_skew += self.bybit_trades_imbalance() * 0.1

        else:
            # Total weight = 0.5
            total_skew += self.bybit_bba_imbalance() * 0.1
            total_skew += self.bybit_mark_wmid_spread() * 0.15
            total_skew += self.bybit_wmid_vamp_spread() * 0.15

            # Total weight = 0.5
            total_skew += self.bybit_orderbook_imbalance() * 0.25
            total_skew += self.bybit_trades_imbalance() * 0.25

        return total_skew
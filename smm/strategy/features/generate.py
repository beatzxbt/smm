
import numpy as np

from frameworks.tools.numba_funcs import nlinspace, nsqrt, nabs, npower
from smm.strategy.features.momentum import momentum_v1, _tick_candles, _combine_trades_arr
from smm.strategy.features.log_spread import log_spread
from smm.strategy.features.bba_imbalance import bba_imbalance

from frameworks.sharedstate.market import MarketDataSharedState


class CalculateFeatures:
    """
    Some features are disabled for Bybit-only streams    
    """

    def __init__(
        self, 
        mdss: MarketDataSharedState, 
        symbol: str
    ) -> None:

        self.mdss = mdss
        self.bybit = self.mdss.bybit[symbol]
        self.binance = self.mdss.binance[symbol]

        self.bybit_trades = self.bybit["trades"]._unwrap()
        self.binance_trades = self.binance["trades"]._unwrap()

        self.depths = np.array([200, 100, 50, 25, 10])
        self.tick_bucket_size = 10


    def _momentum_v1_ticks(self):
        total_ticks = _combine_trades_arr(self.binance_trades, self.bybit_trades)
        tick_candles = _tick_candles(total_ticks, self.tick_bucket_size)
        return momentum_v1(
            candles=tick_candles, 
            lengths=self.depths
        )


    def _bybit_mark_wmid_spread(self):
        return log_spread(
            price=self.bybit["mark_price"], 
            benchmark=self.bybit["wmid_price"]
        )


    def _binance_bybit_wmid_spread(self):
        return log_spread(
            price=self.binance["wmid_price"], 
            benchmark=self.bybit["wmid_price"]
        )

    
    def _bybit_bba_imbalance(self):
        return bba_imbalance(
            bid=self.ss.bybit_bba[0][1], 
            ask=self.ss.bybit_bba[1][1]
        )

    
    def _binance_bba_imbalance(self):
        return bba_imbalance(
            bid=self.ss.binance_bba[0][1], 
            ask=self.ss.binance_bba[1][1]
        )


    def generate_skew(self):
        total_skew = 0

        values = {
            "imbalance": {
                "bybit_bba": self._bybit_bba_imbalance(),
                "binance_bba": self._binance_bba_imbalance(),
            },

            "spread": {
                "bybit_mark-wmid": self._bybit_mark_wmid_spread(),
                "bybit-binance_wmid": self._binance_bybit_wmid_spread(),
            },

            "momentum": {
                "tick_momentum": self._momentum_v1_ticks(),
            }
        }

        if self.ss.primary_data_feed == "BINANCE":
            momentum_weight = 0.4
            bybit_spread_weight = 0.2
            binance_spread_weight = 0.2
            bybit_bba_imb_weight = 0.1
            binance_bba_imb_weight = 0.1

            # Generate all feature values
            total_skew += self._momentum_v1_ticks() * momentum_weight
            total_skew += self._bybit_mark_wmid_spread() * bybit_spread_weight
            total_skew += self._binance_bybit_wmid_spread() * binance_spread_weight
            total_skew += self._bybit_bba_imbalance() * bybit_bba_imb_weight
            total_skew += self._binance_bba_imbalance() * binance_bba_imb_weight

        else:
            momentum_weight = 0.5
            bybit_spread_weight = 0.3
            bybit_bba_imb_weight = 0.2

            # Generate all feature values
            total_skew += self._momentum_v1_ticks() * momentum_weight
            total_skew += self._bybit_mark_wmid_spread() * bybit_spread_weight
            total_skew += self._bybit_bba_imbalance() * bybit_bba_imb_weight

        return total_skew

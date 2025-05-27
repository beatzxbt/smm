import numpy as np

from framework.tools.time import time_s

from smm.strategies.base.engine import BaseFeatureEngine
from smm.features.orderbook_imbalance import OrderbookImbalance
from smm.features.trades_imbalance import TradesTickImbalance, TradesTimeImbalance
from smm.features.trades_excitement import TradesTickExcitement, TradesTimeExcitement


class PlainFeatureEngine(BaseFeatureEngine):
    def __init__(self, params: dict):
        super().__init__(params)

        # Access plain strategy parameters
        plain_params = self._params["parameters"]["plain"]

        # Trade features
        self._trade_tick_imbalance = TradesTickImbalance(
            window=plain_params["trades_tick_imbalance_window"]
        )
        self._trade_time_imbalance = TradesTimeImbalance(
            window=plain_params["trades_time_imbalance_window"]
        )
        self._trade_tick_excitement = TradesTickExcitement(
            short_window=plain_params["trades_tick_excitement_short_window"],
            long_window=plain_params["trades_tick_excitement_long_window"],
            buffer=plain_params["trades_tick_excitement_buffer"]
        )
        self._trade_time_excitement = TradesTimeExcitement(
            short_window=plain_params["trades_time_excitement_short_window"],
            long_window=plain_params["trades_time_excitement_long_window"],
            buffer=plain_params["trades_time_excitement_buffer"]
        )
        
        # Orderbook features
        self._orderbook_imbalance = OrderbookImbalance(
            depth_bps=plain_params["orderbook_imbalance_depth_bps"]
        )

        # Weights must sum up to 1.0
        self._price_feature_weights = {
            "orderbook_imbalance": plain_params.get("orderbook_imbalance_weight", 0.5),
            "trade_tick_imbalance": plain_params.get("trade_tick_imbalance_weight", 0.3),
            "trade_time_imbalance": plain_params.get("trade_time_imbalance_weight", 0.2),
        }

        # Weights must sum up to 1.0
        self._spread_feature_weights = {
            "trade_tick_excitement": plain_params.get("trade_tick_excitement_weight", 0.5),
            "trade_time_excitement": plain_params.get("trade_time_excitement_weight", 0.5)
        }
        self._spread_multiplier = 1.0

    def update_trade(self, event):
        for trade in event.trades:
            self._trade_tick_imbalance.update(trade.time, trade.is_buy, trade.px, trade.sz)
            self._trade_time_imbalance.update(trade.time, trade.is_buy, trade.px, trade.sz)
            self._trade_tick_excitement.update(trade.time, trade.is_buy, trade.px, trade.sz)
            self._trade_time_excitement.update(trade.time, trade.is_buy, trade.px, trade.sz)

        # This automatically selects the last trade in the list
        self.update_last_px(trade.px)
        self.calculate()

    def update_orderbook(self, event, orderbook):
        self._orderbook_imbalance.update(orderbook)
        
        self.update_last_mid_px(orderbook.get_mid_px())
        self.calculate()

    def update_ticker(self, event):
        # If the funding time very close (eg 30s away), we gradually increase 
        # the spread until the funding period resets. This ideally should be
        # a feature, but its simple enough to do here.
        time_to_funding_s = (event.funding_time // 1000) - int(time_s())
        
        if 0 < time_to_funding_s <= 30:
            self._spread_multiplier = 1.0 / np.sqrt(time_to_funding_s)
        else:
            self._spread_multiplier = 1.0
        
        self.calculate()

    def calculate(self):
        self._fair_skew = (
            self._orderbook_imbalance.get_value() * self._price_feature_weights["orderbook_imbalance"] +
            self._trade_tick_imbalance.get_value() * self._price_feature_weights["trade_tick_imbalance"] +
            self._trade_time_imbalance.get_value() * self._price_feature_weights["trade_time_imbalance"]
        )

        self._spread = (
            self._trade_tick_excitement.get_value() * self._spread_feature_weights["trade_tick_excitement"] +
            self._trade_time_excitement.get_value() * self._spread_feature_weights["trade_time_excitement"]
        )
        self._spread *= self._spread_multiplier

    def get_spread(self):
        return self._spread * self._spread_multiplier * self._last_mid_px
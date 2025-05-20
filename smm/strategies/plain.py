import asyncio
import numpy as np

from framework.tools.logger import Logger
from framework.tools.orderbook import Orderbook
from framework.tools.time import time_ms, time_s

from framework.base.exchange import BaseExchange
from framework.base.internal_structs import (
    Trade,
    TradeMsg,
    OrderbookMsg,
    TickerMsg,
    PositionMsg,
    OrderMsg,
    ExecutionMsg,
    AccountMsg,
    HealthCheckMsg,
    MarketDataEvent,
    PrivateDataEvent,
    Event,
)

from smm.strategies.base import BaseStrategy
from smm.features.base_engine import BaseFeatureEngine
from smm.features.orderbook_imbalance import OrderbookImbalance
from smm.features.trades_imbalance import TradesTickImbalance, TradesTimeImbalance
from smm.features.trades_excitement import TradesTickExcitement, TradesTimeExcitement


class PlainFeatureEngine(BaseFeatureEngine):
    def __init__(self, params: dict):
        super().__init__(params)

        # Trade features
        self._trade_tick_imbalance = TradesTickImbalance(window=self._params["trades_tick_imbalance_window"])
        self._trade_time_imbalance = TradesTimeImbalance(window=self._params["trades_time_imbalance_window"])
        self._trade_tick_excitement = TradesTickExcitement(
            short_window=self._params["trades_tick_excitement_short_window"],
            long_window=self._params["trades_tick_excitement_long_window"],
            buffer=self._params["trades_tick_excitement_buffer"]
        )
        self._trade_time_excitement = TradesTimeExcitement(
            short_window=self._params["trades_time_excitement_short_window"],
            long_window=self._params["trades_time_excitement_long_window"],
            buffer=self._params["trades_time_excitement_buffer"]
        )
        
        # Orderbook features
        self._orderbook_imbalance = OrderbookImbalance(depth_bps=self._params["orderbook_imbalance_depth_bps"])

        # Must sum up to 1.0
        self._price_feature_weights = {
            "orderbook_imbalance": self._params["orderbook_imbalance_weight"],
            "trade_tick_imbalance": self._params["trade_tick_imbalance_weight"],
            "trade_time_imbalance": self._params["trade_time_imbalance_weight"],
        }

        # Must sum up to 1.0
        self._spread_feature_weights = {
            "trade_tick_excitement": self._params["trade_tick_excitement_weight"],
            "trade_time_excitement": self._params["trade_time_excitement_weight"]
        }
        self._spread_multiplier = 1.0

    def update_trade(self, event: TradeMsg):
        for trade in event.trades:
            self._trade_tick_imbalance.update(trade.time, trade.is_buy, trade.px, trade.sz)
            self._trade_time_imbalance.update(trade.time, trade.is_buy, trade.px, trade.sz)
            self._trade_tick_excitement.update(trade.time, trade.is_buy, trade.px, trade.sz)
            self._trade_time_excitement.update(trade.time, trade.is_buy, trade.px, trade.sz)

        self.calculate()

    def update_orderbook(self, event: OrderbookMsg, orderbook: Orderbook):
        self._orderbook_imbalance.update(orderbook)
        
        self.calculate()

    def update_ticker(self, event: TickerMsg):
        # If the funding time very close (eg 30s away), we gradually increase 
        # the spread until the funding period resets. This ideally should be
        # a feature, but its simple enough to do here.
        time_to_funding_s = (event.funding_time // 1000) - int(time_s())
        
        if 0 < time_to_funding_s <= 30:
            self._spread_multiplier = 1.0 / np.sqrt(time_to_funding_s)
        else:
            self._spread_multiplier = 1.0
        
        self.calculate()

    def calculate(self) -> float:
        self._fair_px = (
            self._orderbook_imbalance.get_value() * self._price_feature_weights["orderbook_imbalance"] +
            self._trade_tick_imbalance.get_value() * self._price_feature_weights["trade_tick_imbalance"] +
            self._trade_time_imbalance.get_value() * self._price_feature_weights["trade_time_imbalance"]
        )

        self._spread = (
            self._trade_tick_excitement.get_value() * self._spread_feature_weights["trade_tick_excitement"] +
            self._trade_time_excitement.get_value() * self._spread_feature_weights["trade_time_excitement"]
        )
        self._spread *= self._spread_multiplier

    def get_spread(self) -> float:
        return self._spread * self._spread_multiplier
    
    def get_fair_px(self) -> float:
        return self._fair_px


class PlainStrategy(BaseStrategy):
    def __init__(self, exchange: BaseExchange, params: dict, logger: Logger, producer_queues: list[asyncio.Queue]):
        super().__init__(
            exchange=exchange,
            params=params,
            logger=logger,
            producer_queues=producer_queues
        )
        
        # Enfore required parameters for the relevant features and strategy
        # variables. If not present, error should be thrown (better break than silent).
        if "minimum_spread" not in self.params:
            raise ValueError("Missing parameter; expected 'minimum_spread'")
        if "aggressiveness" not in self.params:
            raise ValueError("Missing parameter; expected 'aggressiveness'")

        self._feature_engine = PlainFeatureEngine(params=self.params)
        
        # Strategy override variables
        self._spread_multiplier = 1.0

        # State variables
        self._last_market_data_update = 0.0
        self._last_private_data_update = 0.0
        self._last_health_check = 0.0

        # We maintain the keys to be the cloids, so the exact level can be 
        # quickly checked for existence. Inflight orders maintains a simple
        # mapping of the cloid to px and sz so if the level needs to be updated, 
        # its information can be queried if it really needs to be cancelled or not.
        self._current_orders: dict[str, OrderMsg] = {}
        self._inflight_orders: dict[str, dict[str, float]] = {}

        # The desired orders are a dictionary of {cloid: {px: float, sz: float}}
        # This acts as the target at any given time for the strategy's desired 
        # orders at the exchange. The cloid's will all start with the key prefix
        # 'PLAIN{level}{B/S}' where {level} is the two-digit level of the order
        # and {B/S} is whether it is a buy or sell.
        # eg. PLAIN01B, PLAIN01S, PLAIN02B, PLAIN02S, etc.
        self._desired_orders: dict[str, dict[str, float]] = {}
        for level in range(self.params["total_orders"] // 2):
            for is_buy in [True, False]:
                self._desired_orders.update({
                    f"PLAIN{level}{'B' if is_buy else 'S'}": {
                        "px": 0.0,
                        "sz": 0.0
                    }
                })

        # We maintain the current position in a simple dictionary. This is 
        # solely for inventory tracking, so minimal information needed.
        self._current_position = {
            "px": 0.0,
            "is_long": False,
            "sz": 0.0,
            "age": 0.0
        }

    async def consume_event(self, event: Event, **kwargs):
        if isinstance(event, TickerMsg):
            self.logger.trace(f"TickerMsg received; event: {event}")
            self._feature_engine.update_ticker(event)
            
        elif isinstance(event, TradeMsg):
            self.logger.trace(f"TradeMsg received; event: {event}")
            self._feature_engine.update_trade(event)
                
        elif isinstance(event, OrderbookMsg):
            self.logger.trace(f"OrderbookMsg received; event: {event}")
            if event.is_snapshot:
                self._orderbook.warmup(
                    bids=event.bids,
                    asks=event.asks,
                    seq_id=event.seq_id
                )
            elif event.is_bbo:
                self._orderbook.update_bbo(
                    bid_px=event.bid_px,
                    bid_sz=event.bid_sz,
                    ask_px=event.ask_px,
                    ask_sz=event.ask_sz, 
                    seq_id=event.seq_id
                )
            else:
                self._orderbook.update_full(
                    bids=event.bids,
                    asks=event.asks,
                    seq_id=event.seq_id
                )     
            self._feature_engine.update_orderbook(event, self._orderbook)

        elif isinstance(event, PositionMsg):
            self.logger.trace(f"PositionMsg received; event: {event}")
            self._current_position = {
                "px": event.px,
                "sz": event.sz,
                "age": event.age
            }

        elif isinstance(event, OrderMsg):
            self.logger.trace(f"OrderMsg received; event: {event}")
            if event.is_cancelled:
                self._current_orders.pop(event.oid, None)
            else:
                self._current_orders[event.oid] = event
                
    async def update_state(self, **kwargs):
        # {cloid: {px: float, sz: float}}
        desired_orders = {}

        mid_px = self._orderbook.get_mid_px()
        fair_px = self._feature_engine.get_fair_px()
        spread = self._feature_engine.get_spread()
        
        # If the fair px is X bps away from mid px, we want to take
        # as we believe the edge is > taker fees (ideally plus some margin).
        # Though we only do this if we arent in a heavy position already.
        # For now, this is hardcoded to 10bps but it may become a parameter
        # in the near future.
        edge = abs(fair_px / mid_px) - 1.0
        in_large_position = abs(self._current_position["sz"]) > self.params["max_usd_position"] * 0.5
        if edge > 0.0001 and not in_large_position:
            is_buy = fair_px > mid_px

            # We dont need to add this to the inflight orders, we await it
            # immediately before proceeding.
            await self.exchange.create_order(
                symbol=self.symbol,
                is_maker=False,
                sz=self.params["max_usd_position"] / fair_px,
                is_buy=is_buy,
                tif='GTC',
                cloid=self.exchange.generate_cloid(start=f"PLAIN{99}{'B' if is_buy else 'S'}")
            )
        
        for level in range(self.params["total_orders"] // 2):
            for is_buy in [True, False]:
                cloid = f"PLAIN{str(level).zfill(2)}{'B' if is_buy else 'S'}"
                desired_orders[cloid] = {
                    "px": fair_px + (spread if is_buy else -spread),
                    "is_buy": is_buy,
                    "sz": self.params["max_usd_position"] / desired_orders[cloid]["px"]
                }
    
    async def start(self):
        self.logger.debug("Starting PlainStrategy;")

        while True:
            try:
                event = await self.producer_queue.get()

                if isinstance(event, HealthCheckMsg):
                    if self._health_check_task is not None:
                        self._health_check_task.cancel()
                    self._health_check_task = asyncio.create_task(self.track_health_check(event))
                
                elif isinstance(event, MarketDataEvent):
                    await self.update_features(event)

                elif isinstance(event, PrivateDataEvent):
                    await self.update_state(event)

            except asyncio.CancelledError:
                self.logger.debug("PlainStrategy cancelled;")
                return
            


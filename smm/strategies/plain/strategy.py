import asyncio
import numpy as np

from framework.tools.logger import Logger
from framework.tools.round import Round
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
    OrderTimeInForce,
)

from smm.strategies.base.strategy import BaseStrategy
from smm.strategies.plain.engine import PlainFeatureEngine


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
        self._spread_multiplier = 1.0

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
                self._orderbook.snapshot(
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
                "is_long": event.is_long,
                "sz": event.sz,
                "usd_sz": event.sz * event.px,
                "age": event.age
            }

        elif isinstance(event, OrderMsg):
            self.logger.trace(f"OrderMsg received; event: {event}")
            if event.is_cancelled:
                self._current_orders.pop(event.cloid, None)
            else:
                self._current_orders[event.cloid] = {
                    "px": event.px,
                    "is_buy": event.is_buy,
                    "sz": event.sz
                }
            
            if event.cloid in self._inflight_orders:
                self._inflight_orders.pop(event.cloid)

    async def update_state(self, **kwargs):
        # {cloid: {px: float, sz: float}}
        desired_orders = {}

        mid_px = self._orderbook.get_mid_px()
        fair_skew = self._feature_engine.get_fair_skew()
        spread = self._feature_engine.get_spread()
        
        # If the fair skew is X bps away from mid px, we want to take
        # as we believe the edge is > taker fees (ideally plus some margin).
        # Though we only do this if we arent in a heavy position already.
        # NOTE: This is hardcoded to 10bps but it may become a parameter
        # in the near future.
        in_large_position = self._current_position["usd_sz"] > self.params["max_usd_position"] * 0.5
        if abs(fair_skew) > self.params["taker_skew_threshold"] and not in_large_position:
            is_buy = fair_skew > 0.0

            # We dont need to add this to the inflight orders, we await it
            # immediately before proceeding.
            sz_to_take = (self.params["max_usd_position"] - self._current_position["usd_sz"]) / mid_px
            await self.exchange.create_order(
                symbol=self.symbol,
                is_maker=False,
                sz=self.round.sz(sz_to_take),
                is_buy=is_buy,
                tif=OrderTimeInForce.GTC,
                cloid=self.exchange.generate_cloid(start=f"PLAIN{99}{'B' if is_buy else 'S'}")
            )
        
        # Generate the desired orders for all levels in both directions.
        for level in range(self.params["total_orders"] // 2):
            level_spread = spread * (level + 1)
            level_sz = self.params["max_usd_position"] / self.params["total_orders"]

            for is_buy in [True, False]:
                cloid = f"PLAIN{str(level).zfill(2)}{'B' if is_buy else 'S'}"
                desired_px = mid_px + (level_spread if is_buy else -level_spread)

                desired_orders[cloid] = {
                    "px": desired_px,
                    "is_buy": is_buy,
                    "sz": level_sz / desired_px
                }

        await self.oms.maybe_update_state(desired_orders)

    async def start(self):
        self.logger.debug("Starting PlainStrategy;")

        # Setup the rounding class
        tick_sz, lot_sz = await self.exchange.get_precision(self.symbol)
        self.round = Round(tick_sz=tick_sz, lot_sz=lot_sz)

        while True:
            try:
                event = await self.producer_queue.get()

                if isinstance(event, HealthCheckMsg):
                    if self._health_check_task is not None:
                        self._health_check_task.cancel()
                    self._health_check_task = asyncio.create_task(self.track_health_check(event))
                
                elif isinstance(event, Event):
                    await self.consume_event(event)
                    await self.update_state()

                else: 
                    raise TypeError(f"Unknown event type; {type(event)}")

            except asyncio.CancelledError:
                self.logger.warning("PlainStrategy task cancelled; shutting down gracefully")
                await self.oms.shutdown()
                return
            
            except Exception as e:
                self.logger.error(f"PlainStrategy error; {e}")
                raise e
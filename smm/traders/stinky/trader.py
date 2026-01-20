"""Stinky trader implementation with wide quotes and liquidation.

Usage: selected via config and launched by `python -m smm`.
Components: pricing engine, risk engine, OMS, and volatility helper.
"""

from __future__ import annotations

from framework.base.stream.models import (
    DataMsg,
    ExecutionMsg,
    OrderbookMsg,
    OrderMsg,
    PositionMsg,
    TickerMsg,
    TradeMsg,
)
from mm_toolbox.logging.standard import Logger

from smm.config import AppConfig
from smm.traders.base.trader import BaseTrader
from smm.traders.base.volatility import VolatilityEstimator
from smm.traders.stinky.oms import StinkyOrderManagementSystem
from smm.traders.stinky.pricing import StinkyPricingEngine
from smm.traders.stinky.risk import StinkyRiskEngine


class StinkyTrader(BaseTrader):
    """Trader for the stinky strategy."""

    def __init__(
        self,
        config: AppConfig,
        logger: Logger,
        exchange,
        instrument,
        rounder,
        market_data,
        private_data,
        producer_queues,
    ) -> None:
        """Initialize the stinky trader.

        Args:
            config (AppConfig): Application configuration.
            logger (Logger): Logger instance.
            exchange (Exchange): Exchange client.
            instrument (Instrument): Resolved instrument.
            rounder (Rounder): Price/size rounder.
            market_data (MarketDataStream): Market data stream.
            private_data (PrivateDataStream): Private data stream.
            producer_queues (list[asyncio.Queue[Msg]]): Queues for stream messages.
        """
        super().__init__(
            config=config,
            logger=logger,
            exchange=exchange,
            instrument=instrument,
            rounder=rounder,
            market_data=market_data,
            private_data=private_data,
            producer_queues=producer_queues,
        )

        self.volatility = VolatilityEstimator(config.volatility)
        self.pricing_engine = StinkyPricingEngine(
            instrument=instrument,
            config=config.pricing,
            stinky_config=config.stinky,
            rounder=rounder,
            volatility=self.volatility,
        )
        self.risk_engine = StinkyRiskEngine(config=config.risk)
        self.oms = StinkyOrderManagementSystem(
            instrument=instrument,
            exchange=exchange,
            logger=logger,
            config=config.oms,
            stinky_config=config.stinky,
        )

    async def consume_msg(self, msg: DataMsg) -> None:
        """Consume a data message from the streams.

        Args:
            msg (DataMsg): Data message to process.
        """
        if self.is_stale(msg, buffer_ms=250):
            return
        match msg:
            case TradeMsg():
                self.pricing_engine.consume_trade(msg)
            case OrderbookMsg():
                self.pricing_engine.consume_orderbook(msg)
                self.risk_engine.consume_orderbook(msg)
            case TickerMsg():
                self.pricing_engine.consume_ticker(msg)
            case PositionMsg():
                self.pricing_engine.consume_position(msg)
                self.risk_engine.consume_position(msg)
                self.oms.consume_position(msg)
            case OrderMsg():
                self.oms.consume_order(msg)
                self.risk_engine.consume_orders(msg)
            case ExecutionMsg():
                self.oms.consume_execution(msg)

    async def update_state(self) -> None:
        """Generate desired state and update the OMS."""
        desired = self.pricing_engine.generate_desired_state()
        if not self.risk_engine.try_approve_desired_state(desired, force=False):
            return
        await self.oms.try_update_state(desired)

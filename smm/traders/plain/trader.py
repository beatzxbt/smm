"""Plain trader implementation that wires pricing, risk, and OMS.

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
from smm.traders.plain.oms import PlainOrderManagementSystem
from smm.traders.plain.pricing import PlainPricingEngine
from smm.traders.plain.risk import PlainRiskEngine


class PlainTrader(BaseTrader):
    """Trader for the plain strategy."""

    oms: PlainOrderManagementSystem

    def __init__(
        self,
        config: AppConfig,
        logger: Logger,
        exchange,
        instrument,
        rounder,
        market_data,
        private_data,
        producer_buffer,
    ) -> None:
        """Initialize the plain trader.

        Args:
            config (AppConfig): Application configuration.
            logger (Logger): Logger instance.
            exchange (Exchange): Exchange client.
            instrument (Instrument): Resolved instrument.
            rounder (Rounder): Price/size rounder.
            market_data (MarketDataStream): Market data stream.
            private_data (PrivateDataStream): Private data stream.
            producer_buffer: Ring buffer for stream messages.
        """
        super().__init__(
            config=config,
            logger=logger,
            exchange=exchange,
            instrument=instrument,
            rounder=rounder,
            market_data=market_data,
            private_data=private_data,
            producer_buffer=producer_buffer,
        )

        self.volatility = VolatilityEstimator(config.volatility)
        self.pricing_engine = PlainPricingEngine(
            instrument=instrument,
            config=config.pricing,
            plain_config=config.plain,
            rounder=rounder,
            volatility=self.volatility,
        )
        self.risk_engine = PlainRiskEngine(config=config.risk)
        self.oms = PlainOrderManagementSystem(
            instrument=instrument,
            exchange=exchange,
            logger=logger,
            config=config.oms,
        )

    async def consume_msg(self, msg: DataMsg) -> None:
        """Consume a data message from the streams.

        Args:
            msg (DataMsg): Data message to process.

        """
        if self.is_stale(msg, buffer_ms=100):
            return
        match msg:
            case TradeMsg():
                self.pricing_engine.consume_msg(msg)
            case OrderbookMsg():
                self.pricing_engine.consume_msg(msg)
                self.risk_engine.consume_msg(msg)
            case TickerMsg():
                self.pricing_engine.consume_msg(msg)
            case PositionMsg():
                self.pricing_engine.consume_msg(msg)
                self.risk_engine.consume_msg(msg)
                self.oms.consume_msg(msg)
            case OrderMsg():
                self.oms.consume_msg(msg)
                self.risk_engine.consume_msg(msg)
            case ExecutionMsg():
                self.oms.consume_msg(msg)

    async def update_state(self) -> None:
        """Generate desired state and update the OMS."""
        desired = self.pricing_engine.generate_desired_state()
        if not self.risk_engine.try_approve_desired_state(desired, force=False):
            return
        await self.oms.try_update_state(desired)

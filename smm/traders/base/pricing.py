"""Abstract pricing engine interface for traders.

Usage: implement consume_* hooks and emit DesiredState for OMS.
Components: BasePricingEngine abstract methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from framework.base.common import Instrument
from framework.base.stream.models import OrderbookMsg, PositionMsg, TickerMsg, TradeMsg

from smm.config import PricingConfig
from smm.traders.base.types import DesiredState


class BasePricingEngine(ABC):
    """Base class for pricing engines used by traders.

    Attributes:
        instrument (Instrument): Instrument traded by the engine.
        config (PricingConfig): Pricing configuration settings.
    """

    def __init__(self, instrument: Instrument, config: PricingConfig) -> None:
        """Initialize the pricing engine.

        Args:
            instrument (Instrument): Instrument traded by the engine.
            config (PricingConfig): Pricing configuration settings.
        """
        self.instrument = instrument
        self.config = config

    @abstractmethod
    def consume_trade(self, msg: TradeMsg) -> None:
        """Consume a trade message.

        Args:
            msg (TradeMsg): Trade message from the exchange.

        Returns:
            None.
        """

    @abstractmethod
    def consume_orderbook(self, msg: OrderbookMsg) -> None:
        """Consume an orderbook message.

        Args:
            msg (OrderbookMsg): Orderbook message from the exchange.

        Returns:
            None.
        """

    @abstractmethod
    def consume_ticker(self, msg: TickerMsg) -> None:
        """Consume a ticker message.

        Args:
            msg (TickerMsg): Ticker message from the exchange.

        Returns:
            None.
        """

    @abstractmethod
    def consume_position(self, msg: PositionMsg) -> None:
        """Consume a position message.

        Args:
            msg (PositionMsg): Position message from the exchange.

        Returns:
            None.
        """

    @abstractmethod
    def generate_desired_state(self) -> DesiredState:
        """Generate the desired state from current signals.

        Returns:
            DesiredState: Desired state for the OMS to reconcile.
        """

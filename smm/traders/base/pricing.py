"""Abstract pricing engine interface for traders.

Usage: implement consume_msg and emit DesiredState for OMS.
Components: BasePricingEngine abstract methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from framework.base.common import Instrument
from framework.base.stream.models import DataMsg

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
    def consume_msg(self, msg: DataMsg) -> None:
        """Consume a pricing-relevant stream message.

        Args:
            msg (DataMsg): Stream message consumed by pricing.
        """

    @abstractmethod
    def generate_desired_state(self) -> DesiredState:
        """Generate the desired state from current signals.

        Returns:
            DesiredState: Desired state for the OMS to reconcile.
        """

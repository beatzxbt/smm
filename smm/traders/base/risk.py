"""Abstract risk engine interface for traders.

Usage: consume market/private data and approve desired states.
Components: BaseRiskEngine abstract checks and helpers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from framework.base.stream.models import OrderMsg, OrderbookMsg, PositionMsg

from smm.config import RiskConfig
from smm.traders.base.types import DesiredState


class BaseRiskEngine(ABC):
    """Base class for trader risk engines.

    Attributes:
        config (RiskConfig): Risk configuration settings.
        mid_price (float): Latest mid price.
        position_size (float): Signed base position size.
    """

    def __init__(self, config: RiskConfig) -> None:
        """Initialize the risk engine.

        Args:
            config (RiskConfig): Risk configuration settings.
        """
        self.config = config
        self.mid_price: float = 0.0
        self.position_size: float = 0.0

    def update_mid_price(self, mid_price: float) -> None:
        """Update the cached mid price.

        Args:
            mid_price (float): Current mid price.

        Returns:
            None.
        """
        if mid_price > 0.0:
            self.mid_price = mid_price

    def update_position(self, position: PositionMsg) -> None:
        """Update the cached position size.

        Args:
            position (PositionMsg): Latest position message.

        Returns:
            None.
        """
        signed_size = position.size if position.is_long else -position.size
        self.position_size = signed_size

    def net_inventory_quote(self) -> float:
        """Return the signed inventory in quote terms.

        Returns:
            float: Signed inventory value in quote currency.
        """
        if self.mid_price <= 0.0:
            return 0.0
        return self.position_size * self.mid_price

    @abstractmethod
    def consume_orderbook(self, msg: OrderbookMsg) -> None:
        """Consume an orderbook message.

        Args:
            msg (OrderbookMsg): Orderbook message from the exchange.

        Returns:
            None.
        """

    @abstractmethod
    def consume_orders(self, msg: OrderMsg) -> None:
        """Consume an order update message.

        Args:
            msg (OrderMsg): Order message from the exchange.

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
    def try_approve_desired_state(
        self, desired_state: DesiredState, force: bool = False
    ) -> bool:
        """Validate a desired state against risk limits.

        Args:
            desired_state (DesiredState): Desired state proposed by pricing.
            force (bool): Whether to bypass readiness checks.

        Returns:
            bool: True if desired state is approved, False otherwise.
        """

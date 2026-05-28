"""Abstract risk engine interface for traders.

Usage: consume market/private data and approve desired states.
Components: BaseRiskEngine abstract checks and helpers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from framework.base.stream.models import DataMsg, PositionMsg

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

        """
        if mid_price > 0.0:
            self.mid_price = mid_price

    def update_position(self, position: PositionMsg) -> None:
        """Update the cached position size.

        Args:
            position (PositionMsg): Latest position message.

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
    def consume_msg(self, msg: DataMsg) -> None:
        """Consume a risk-relevant stream message.

        Args:
            msg (DataMsg): Stream message consumed by risk.

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

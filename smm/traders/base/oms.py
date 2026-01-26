"""Base OMS interface with rate-limited order actions.

Usage: implement reconciliation and hook into trader update loop.
Components: BaseOrderManagementSystem with token bucket helpers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from framework.base.trading.exchange import Exchange
from framework.base.tools.rate_limiter import RateLimiter
from framework.base.stream.models import ExecutionMsg, OrderMsg, PositionMsg
from mm_toolbox.logging.standard import Logger

from smm.config import OmsBudgetConfig, OmsConfig, RateWindow
from smm.traders.base.types import DesiredState


class BaseOrderManagementSystem(ABC):
    """Base order management system for reconciling desired state.

    Attributes:
        exchange (Exchange): Exchange client.
        logger (Logger): Logger instance.
        config (OmsConfig): OMS configuration settings.
        inflight_orders (dict[str, dict[str, float | bool]]): Orders awaiting confirmation.
        current_orders (dict[str, dict[str, float | bool]]): Live order snapshot.
    """

    def __init__(
        self,
        exchange: Exchange,
        logger: Logger,
        config: OmsConfig,
    ) -> None:
        """Initialize the OMS.

        Args:
            exchange (Exchange): Exchange client for order actions.
            logger (Logger): Logger for status and error messages.
            config (OmsConfig): OMS configuration and budgets.
        """
        self.exchange = exchange
        self.logger = logger
        self.config = config

        self.inflight_orders: dict[str, dict[str, float | bool]] = {}
        self.current_orders: dict[str, dict[str, float | bool]] = {}

        self._create_limiter = self._build_limiter(config.create)
        self._amend_limiter = self._build_limiter(config.amend)
        self._cancel_limiter = self._build_limiter(config.cancel)

    def _build_limiter(self, budget: OmsBudgetConfig) -> RateLimiter:
        """Build a token bucket limiter from budget settings.

        Args:
            budget (OmsBudgetConfig): OMS budget configuration.

        Returns:
            RateLimiter: Token bucket rate limiter.

        Raises:
            ValueError: If per-minute rate would be less than 1 req/sec.
        """
        if budget.per == RateWindow.SEC:
            rate_per_sec = budget.limit
        else:
            # Per-minute: validate that rate is >= 1 req/sec
            if budget.limit < 60:
                raise ValueError(
                    f"Per-minute rate limit must be >= 60 (got {budget.limit}). "
                    f"This would result in < 1 req/sec."
                )
            rate_per_sec = budget.limit // 60
        return RateLimiter(rate_per_sec=rate_per_sec, capacity=rate_per_sec)

    def try_acquire_create(self, tokens: int = 1) -> bool:
        """Attempt to consume create order budget tokens.

        Args:
            tokens (int): Token count to acquire.

        Returns:
            bool: True if tokens were acquired, False otherwise.
        """
        return self._create_limiter.try_acquire(tokens)

    def try_acquire_amend(self, tokens: int = 1) -> bool:
        """Attempt to consume amend order budget tokens.

        Args:
            tokens (int): Token count to acquire.

        Returns:
            bool: True if tokens were acquired, False otherwise.
        """
        return self._amend_limiter.try_acquire(tokens)

    def try_acquire_cancel(self, tokens: int = 1) -> bool:
        """Attempt to consume cancel order budget tokens.

        Args:
            tokens (int): Token count to acquire.

        Returns:
            bool: True if tokens were acquired, False otherwise.
        """
        return self._cancel_limiter.try_acquire(tokens)

    @abstractmethod
    def consume_order(self, msg: OrderMsg) -> None:
        """Consume an order update message.

        Args:
            msg (OrderMsg): Order update message.

        Returns:
            None.
        """

    @abstractmethod
    def consume_position(self, msg: PositionMsg) -> None:
        """Consume a position update message.

        Args:
            msg (PositionMsg): Position update message.

        Returns:
            None.
        """

    @abstractmethod
    def consume_execution(self, msg: ExecutionMsg) -> None:
        """Consume an execution update message.

        Args:
            msg (ExecutionMsg): Execution update message.

        Returns:
            None.
        """

    @abstractmethod
    async def try_update_state(self, desired_state: DesiredState) -> None:
        """Reconcile exchange state to the desired state.

        Args:
            desired_state (DesiredState): Desired state produced by pricing.

        Returns:
            None.
        """

    @abstractmethod
    async def kill_switch(self) -> None:
        """Cancel all orders and attempt to flatten positions.

        Returns:
            None.
        """

"""Risk engine for the plain trader.

Usage: gate desired states before OMS reconciliation.
Components: mid-price tracking and inventory guards.
"""

from __future__ import annotations

from framework.base.stream.models import OrderMsg, OrderbookMsg, PositionMsg

from smm.traders.base.risk import BaseRiskEngine
from smm.traders.base.types import DesiredState


class PlainRiskEngine(BaseRiskEngine):
    """Risk engine that enforces basic quoting limits."""

    def consume_orderbook(self, msg: OrderbookMsg) -> None:
        """Consume an orderbook message.

        Args:
            msg (OrderbookMsg): Orderbook message.

        Returns:
            None.
        """
        if not msg.bids or not msg.asks:
            return
        best_bid = msg.bids[-1].price
        best_ask = msg.asks[0].price
        self.update_mid_price((best_bid + best_ask) / 2.0)

    def consume_orders(self, msg: OrderMsg) -> None:
        """Consume an order update message.

        Args:
            msg (OrderMsg): Order update message.

        Returns:
            None.
        """
        return

    def consume_position(self, msg: PositionMsg) -> None:
        """Consume a position update message.

        Args:
            msg (PositionMsg): Position update message.

        Returns:
            None.
        """
        self.update_position(msg)

    def try_approve_desired_state(
        self, desired_state: DesiredState, force: bool = False
    ) -> bool:
        """Validate desired orders against risk controls.

        Args:
            desired_state (DesiredState): Desired state proposed by pricing.
            force (bool): Whether to bypass readiness checks.

        Returns:
            bool: True if desired state is approved.
        """
        if self.mid_price <= 0.0 and not force:
            return False

        total_orders = len(desired_state.bids) + len(desired_state.asks)
        if total_orders > self.config.max_open_orders:
            return False

        for order in desired_state.bids + desired_state.asks:
            if order.price <= 0.0 or order.size <= 0.0:
                return False
            distance_pct = abs(order.price - self.mid_price) / self.mid_price * 100.0
            if distance_pct > self.config.max_order_distance_pct:
                return False

        if abs(self.net_inventory_quote()) > self.config.max_inventory_quote:
            return False

        return True

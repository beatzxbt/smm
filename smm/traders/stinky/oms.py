"""OMS implementation for the stinky trader with liquidation logic.

Usage: reconcile stinky quotes and execute liquidation orders.
Components: order tracking, liquidation queue, rate limits.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from framework.base.common import ClientOrderId, Instrument
from framework.base.stream.models import (
    DataMsg,
    ExecutionMsg,
    OrderMsg,
    OrderTimeInForce,
    PositionMsg,
)
from framework.base.trading.models import AmendOrder, CancelOrder, CreateOrder
from mm_toolbox.logging.standard import Logger
from mm_toolbox.time import time_s

from smm.config import OmsConfig, StinkyConfig
from smm.traders.base.oms import BaseOrderManagementSystem
from smm.traders.base.types import DesiredState


@dataclass
class InventoryPosition:
    """Inventory lot tracked for liquidation.

    Attributes:
        size (float): Signed base position size.
        entry_time_s (float): Entry timestamp in seconds.
        is_large (bool): Whether the fill is considered large.
        remaining_size (float): Remaining base size to liquidate.
    """

    size: float
    entry_time_s: float
    is_large: bool
    remaining_size: float


class StinkyOrderManagementSystem(BaseOrderManagementSystem):
    """OMS that handles stinky quotes and inventory liquidations.

    Attributes:
        instrument (Instrument): Instrument traded by the OMS.
    """

    def __init__(
        self,
        instrument: Instrument,
        exchange,
        logger: Logger,
        config: OmsConfig,
        stinky_config: StinkyConfig,
    ) -> None:
        """Initialize the stinky OMS.

        Args:
            instrument (Instrument): Instrument traded by the OMS.
            exchange (Exchange): Exchange client.
            logger (Logger): Logger instance.
            config (OmsConfig): OMS configuration.
            stinky_config (StinkyConfig): Stinky-specific configuration.
        """
        super().__init__(exchange=exchange, logger=logger, config=config)
        self.instrument = instrument
        self._stinky_config = stinky_config
        self._inventory_positions: list[InventoryPosition] = []

    def consume_msg(self, msg: DataMsg) -> None:
        """Consume an OMS-relevant stream message.

        Args:
            msg (DataMsg): Stream message consumed by the OMS.

        """
        match msg:
            case OrderMsg():
                for order in msg.orders:
                    key = order.client_order_id or order.order_id
                    if order.is_cancelled:
                        self.inflight_orders.pop(key, None)
                        self.current_orders.pop(key, None)
                        continue

                    self.inflight_orders.pop(key, None)
                    self.current_orders[key] = {
                        "price": order.price,
                        "is_buy": order.is_buy,
                        "size": order.size_remaining,
                    }
            case PositionMsg():
                return
            case ExecutionMsg():
                for execution in msg.executions:
                    fill_value = execution.price * execution.size
                    is_large = (
                        fill_value
                        >= self._stinky_config.large_fill_threshold_quote
                    )
                    signed_size = (
                        execution.size if execution.is_buy else -execution.size
                    )
                    # Anchor the liquidation wait on the local receive time.
                    # Exchange execution timestamps may lag local receive
                    # time, so the fill is only actionable once we have it.
                    entry_time_s = msg.moments.recv_time_ns / 1_000_000_000.0
                    self._inventory_positions.append(
                        InventoryPosition(
                            size=signed_size,
                            entry_time_s=entry_time_s,
                            is_large=is_large,
                            remaining_size=abs(signed_size),
                        )
                    )

    async def try_update_state(self, desired_state: DesiredState) -> None:
        """Reconcile live orders and execute liquidations.

        Args:
            desired_state (DesiredState): Desired state produced by pricing.

        """
        tasks: list[asyncio.Task] = []
        for order in self._collect_liquidations():
            if self.try_acquire_create():
                tasks.append(asyncio.create_task(self.exchange.create_order(order)))

        tasks.extend(self._reconcile_quotes(desired_state))

        if tasks:
            await asyncio.gather(*tasks)

    async def kill_switch(self) -> None:
        """Cancel all tracked orders."""
        tasks: list[asyncio.Task] = []
        for cloid in list(self.current_orders.keys()):
            if self.try_acquire_cancel():
                tasks.append(
                    asyncio.create_task(
                        self.exchange.cancel_order(
                            CancelOrder(
                                instrument=self.instrument,
                                client_order_id=ClientOrderId(str(cloid)),
                            )
                        )
                    )
                )
        if tasks:
            await asyncio.gather(*tasks)
        self.inflight_orders.clear()
        self.current_orders.clear()
        self._inventory_positions.clear()

    def _collect_liquidations(self) -> list[CreateOrder]:
        """Collect liquidation orders for ready inventory lots.

        Returns:
            list[CreateOrder]: Create orders for liquidation.
        """
        now_s = time_s()
        liquidation_orders: list[CreateOrder] = []
        remaining_positions: list[InventoryPosition] = []

        for position in self._inventory_positions:
            wait_s = (
                self._stinky_config.large_fill_wait_s
                if position.is_large
                else self._stinky_config.small_fill_wait_s
            )
            if now_s - position.entry_time_s < wait_s:
                remaining_positions.append(position)
                continue

            if position.remaining_size <= 0.0:
                continue

            is_buy = position.size < 0.0
            liquidation_orders.append(
                CreateOrder(
                    instrument=self.instrument,
                    size=position.remaining_size,
                    is_buy=is_buy,
                    is_maker=False,
                    tif=OrderTimeInForce.IOC,
                    reduce_only=True,
                    price=None,
                    client_order_id=self.exchange.generate_cloid(
                        prefix=f"{self._stinky_config.cloid_prefix}L"
                    ),
                )
            )

        self._inventory_positions = remaining_positions
        return liquidation_orders

    def _reconcile_quotes(self, desired_state: DesiredState) -> list[asyncio.Task]:
        """Reconcile quote orders to the desired state.

        Args:
            desired_state (DesiredState): Desired state produced by pricing.

        Returns:
            list[asyncio.Task]: Order tasks to execute.
        """
        tasks: list[asyncio.Task] = []

        desired_by_id: dict[str, tuple[float, bool, float]] = {}
        for order in desired_state.bids + desired_state.asks:
            if order.client_order_id is None:
                continue
            desired_by_id[order.client_order_id] = (
                order.price,
                order.is_buy,
                order.size,
            )

        for cloid, live in list(self.current_orders.items()):
            if cloid not in desired_by_id:
                if self.try_acquire_cancel():
                    tasks.append(
                        asyncio.create_task(
                            self.exchange.cancel_order(
                                CancelOrder(
                                    instrument=self.instrument,
                                    client_order_id=ClientOrderId(str(cloid)),
                                )
                            )
                        )
                    )
                    self.current_orders.pop(cloid, None)
                continue

            desired_price, _is_buy, desired_size = desired_by_id[cloid]
            price_changed = not self._within_buffer(live["price"], desired_price)
            size_changed = abs(live["size"] - desired_size) > 0.0

            if price_changed or size_changed:
                if self.try_acquire_amend():
                    tasks.append(
                        asyncio.create_task(
                            self.exchange.amend_order(
                                AmendOrder(
                                    instrument=self.instrument,
                                    size=desired_size,
                                    price=desired_price,
                                    client_order_id=ClientOrderId(str(cloid)),
                                )
                            )
                        )
                    )
                    self.current_orders[cloid] = {
                        "price": desired_price,
                        "is_buy": live["is_buy"],
                        "size": desired_size,
                    }

        for cloid, (price, is_buy, size) in desired_by_id.items():
            if cloid in self.current_orders or cloid in self.inflight_orders:
                continue
            if self.try_acquire_create():
                tasks.append(
                    asyncio.create_task(
                        self.exchange.create_order(
                            CreateOrder(
                                instrument=self.instrument,
                                size=size,
                                is_buy=is_buy,
                                is_maker=True,
                                tif=OrderTimeInForce.GTC,
                                reduce_only=False,
                                price=price,
                                client_order_id=ClientOrderId(str(cloid)),
                            )
                        )
                    )
                )
                self.inflight_orders[cloid] = {
                    "price": price,
                    "is_buy": is_buy,
                    "size": size,
                }

        return tasks

    def _within_buffer(self, live_price: float, desired_price: float) -> bool:
        """Return True if the desired price is within buffer bps.

        Args:
            live_price (float): Current live price.
            desired_price (float): Desired price.

        Returns:
            bool: True if within buffer, False otherwise.
        """
        buffer = self.config.price_buffer_bps / 10_000.0
        return (
            (desired_price * (1.0 - buffer))
            <= live_price
            <= (desired_price * (1.0 + buffer))
        )

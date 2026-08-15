"""OMS implementation for the plain trader.

Usage: reconcile desired quotes via create/amend/cancel.
Components: order tracking, buffer checks, and rate limits.
"""

from __future__ import annotations

import asyncio

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

from smm.config import OmsConfig
from smm.traders.base.oms import BaseOrderManagementSystem
from smm.traders.base.types import DesiredState


class PlainOrderManagementSystem(BaseOrderManagementSystem):
    """OMS that reconciles plain quotes using create/amend/cancel.

    Attributes:
        instrument (Instrument): Instrument traded by the OMS.
    """

    def __init__(
        self,
        instrument: Instrument,
        exchange,
        logger: Logger,
        config: OmsConfig,
    ) -> None:
        """Initialize the plain OMS.

        Args:
            instrument (Instrument): Instrument traded by the OMS.
            exchange (Exchange): Exchange client.
            logger (Logger): Logger instance.
            config (OmsConfig): OMS configuration.
        """
        super().__init__(exchange=exchange, logger=logger, config=config)
        self.instrument = instrument

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
                return

    async def try_update_state(self, desired_state: DesiredState) -> None:
        """Reconcile live orders against the desired state.

        Args:
            desired_state (DesiredState): Desired state produced by pricing.

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
                self.inflight_orders[cloid] = {
                    "price": price,
                    "is_buy": is_buy,
                    "size": size,
                }
                tasks.append(
                    asyncio.create_task(
                        self._create_and_track(
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

        if tasks:
            await asyncio.gather(*tasks)

    async def _create_and_track(self, create_order: CreateOrder) -> None:
        """Submit a create order and update inflight tracking on outcome.

        A rejected create is dropped from inflight tracking so the next
        reconciliation cycle retries it.

        Args:
            create_order (CreateOrder): Create order to submit.
        """
        cloid = str(create_order.client_order_id)
        response = await self.exchange.create_order(create_order)
        if not response.is_successful:
            self.inflight_orders.pop(cloid, None)
            self.logger.warning(
                f"Order create rejected for {cloid}; will retry on next "
                f"cycle; {response.err_msg}"
            )

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

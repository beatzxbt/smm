import asyncio
from typing import Coroutine

from framework.base.internal_structs import OrderTimeInForce

from smm.strategies.base.oms import BaseOrderManagementSystem, DesiredOrder

class PlainOrderManagementSystem(BaseOrderManagementSystem):
    def __init__(self, exchange, logger):
        super().__init__(
            exchange=exchange, logger=logger
        )

    def consume_order_event(self, event):
        if event.is_cancelled:
            self._inflight_orders.pop(event.cloid, None)
            self._current_orders.pop(event.cloid, None)

        # We maintain the keys to be the cloids, so the exact level can be 
        # quickly checked for existence. Inflight orders maintains a simple
        # mapping of the cloid to px and sz so if the level needs to be updated, 
        # its information can be queried if it really needs to be cancelled or not.
        if event.cloid in self._inflight_orders:
            self._inflight_orders.pop(event.cloid)
            self._current_orders[event.cloid] = {
                "px": event.px,
                "is_buy": event.is_buy,
                "sz": event.sz
            }
        
        # We dont want to track orders that the algorithm hasnt 
        # explicitly requested, so log these as warnings for later.
        else:
            self.logger.warning(f"Unintentional order detected; event: {event}")

    def consume_position_event(self, event):
        self._current_position.update({
            "px": event.px,
            "is_long": event.is_long,
            "sz": event.sz,
            "usd_sz": event.sz * event.px,
            "age": event.age
        })
    
    def consume_execution_event(self, event):
        if event.cloid in self._current_orders:
            self._current_orders[event.cloid]["sz"] -= event.sz
            if self._current_orders[event.cloid]["sz"] == 0:
                self._current_orders.pop(event.cloid)

            if event.is_buy:
                self._current_position_state["sz"] += event.sz
            else:
                self._current_position_state["sz"] -= event.sz

    def _is_within_bounds(self, px: float, bench_px: float, buffer_bps: float=5.0) -> bool:
        """Check if price is within ±buffer_bps of fair price.
        
        Args:
            buffer_bps: Buffer in basis points (0.01% = 1 bps)
            price: Price to check

        Returns:
            bool: True if price is within bounds, False otherwise
        """
        buffer_decimal = buffer_bps / 10000.0
        lower_bound = bench_px * (1.0 - buffer_decimal)
        upper_bound = bench_px * (1.0 + buffer_decimal)
        return lower_bound <= px <= upper_bound
    
    async def maybe_update_state(self, desired_orders: list[DesiredOrder]):
        order_tasks: list[Coroutine] = []

        for desired_order in desired_orders:
            # If the order is inflight, we need to check if its price is within bounds.
            # If it is, we update the order, otherwise we cancel it.
            if desired_order.cloid in self._inflight_orders:
                inflight_order = self._inflight_orders[desired_order.cloid]
                if not self._is_within_bounds(inflight_order.px, desired_order.px):
                    order_tasks.append(
                        self.exchange.cancel_order(
                            symbol=self.symbol,
                            cloid=desired_order.cloid,
                        )
                    )
                    desired_orders.pop(desired_order.cloid)
                    order_tasks.append(
                        self.exchange.create_order(
                            symbol=self.symbol,
                            is_maker=True,
                            sz=desired_order.sz,
                            is_buy=desired_order.is_buy,
                            px=desired_order.px,
                            tif=OrderTimeInForce.GTC,
                            cloid=desired_order.cloid,
                        )
                    )
                    self._inflight_orders.update({desired_order.cloid: desired_order})

            # If the order is not found in the current orders, its either missing 
            # or been filled. Either way, we need to create a new order.
            if desired_order.cloid not in self._current_orders:
                order_tasks.append(
                    self.exchange.create_order(
                        symbol=self.symbol,
                        is_maker=True,
                        sz=desired_order.sz,
                        is_buy=desired_order.is_buy,
                        px=desired_order.px,
                        tif=OrderTimeInForce.GTC,
                        cloid=desired_order.cloid,
                    )
                )
                self._inflight_orders.update({desired_order.cloid: desired_order})

            # If the order is found in the current orders, we need to amend it
            # if the px or sz has changed sufficiently.
            if desired_order.cloid in self._current_orders:
                current_order = self._current_orders[desired_order.cloid]
                px_changed = not self._is_within_bounds(current_order.px, desired_order.px)
                sz_changed = not self._is_within_bounds(current_order.sz, desired_order.sz, buffer_bps=1000)
                
                if px_changed or sz_changed:
                    order_tasks.append(
                        self.exchange.amend_order(
                            symbol=self.symbol,
                            sz=desired_order.sz,
                            px=desired_order.px,
                            cloid=desired_order.cloid,
                        )
                    )

        await asyncio.gather(*order_tasks)

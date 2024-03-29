import asyncio
import numpy as np
from frameworks.sharedstate import SharedState
from smm.strategy.inventory import InventoryTools
from typing import Dict, List, Tuple, Union, Coroutine


class OrderManagementSystem:
    """
    Written to spec: [https://twitter.com/BeatzXBT/status/1731757053113147524]
    """

    def __init__(self, ss: SharedState, pair: Tuple[str, str]) -> None:
        self.ss = ss
        self.exchange, self.symbol = pair
        self.logging = self.ss.logging

        self.client = self._client_()
        self.it = InventoryTools() # TODO: Add the max position somehow here
        
        self.current_bba = None
        self.current_outer = None
        self.new_bba = None
        self.new_outer = None   

        self.rate_limits = None
        self._update_local_rate_limits_()

    def _client_(self):
        """Reference the correct exchange client in sharedstate"""
        return self.ss.clients[self.exchange]["order_client"]
    
    @property
    def __market__(self) -> Dict:
        return self.ss.market[self.exchange][self.symbol]

    @property
    def __private__(self) -> Dict:
        return self.ss.private[self.exchange][self.symbol]

    @property
    def __api__(self) -> Dict:
        return self.ss.private[self.exchange]["API"]

    @property
    def __current_delta__(self) -> float:
        """Calculate current inventory delta"""
        return self.it.position_to_delta(self.__private__["currentPosition"])
    
    @property
    def __current_latency__(self) -> float:
        return np.mean(self.__api__["latency"]._unwrap())

    def _total_rate_limits_remaining_(self) -> Tuple[int, int]:
        """Total (replaces, amends) remaining"""
        return (
            min(self.rate_limits["create"], self.rate_limits["cancel"]),
            self.rate_limits["amend"]
        )

    def _split_current_orders_(self) -> Tuple[List, List]:
        """
        Split current orders into BBA/Outer

        Single order struct: (side, price, qty, orderId)

        Output (Tuple):
            [0] = [BidOrder, AskOrder]
            [1] = [[Bid1, Bid2, ...], [Ask1, Ask2, ...]]
        """
        pass
    
    def _update_current_orders_(self) -> None:
        """
        Point to current orders in sharedstate

        Run self._split_current_orders_() on it
        """
        pass
    
    def _update_local_rate_limits_(self) -> None:
        """Refresh cached rate limit state"""
        
        if self.rate_limits is None:
            # 'None' will be replaced with rate limit info stored in 
            # the exchange["API"]. this is just a local snapshot that
            # will be used to manage limits for this cycle. to be ran 
            # at the start of each cycle.
            self.rate_limits = {
                "create": None, 
                "amend": None,
                "cancel": None,
                "cancel_all": None
            }

    def _generate_buffer_bounds_(self, value, benchmark, sensitivity) -> Tuple[float, float]:
        """Produces lower and upper bounds relative to distance from benchmark"""
        diff = benchmark/value if benchmark > value else value/benchmark
        diff *= sensitivity
        return value - diff, value + diff

    def _bounds_checker_(self, value, benchmark, sensitivity=0.1) -> bool:
        """True within non-strict bounds, False otherwise"""
        lower, upper = self._generate_buffer_bounds_(value, benchmark, sensitivity)
        return lower <= value and upper >= value

    async def _limit_order_(self, order: NDArray) -> asyncio.Task:
        """Initiate limit order task to client"""
        return asyncio.create_task(self.client.order_limit(order))

    async def _bba_order_(self, order, orderId) -> List[asyncio.Task]:
        """Attempt amend order, with replace fallback, with cancel all fallback"""

        if self.rate_limits["amend"] > 0:
            return [asyncio.create_task(self.client.order_amend(orderId, order))]
        elif self.__total_rate_limits_remaining__ > 0:
            return [
                asyncio.create_task(self.client.order_cancel(orderId)),
                asyncio.create_task(self.client.order_limit(orderId, order))
            ]
        else:
            return [asyncio.create_task(self.client.order_cancel_all())]

    async def _outer_order_(self, order, orderId) -> List[asyncio.Task]:
        """Attempt replace order, with cancel fallback, with cancel all fallback"""
        if self.__total_rate_limits_remaining__[1] > 0:
            return [
                asyncio.create_task(self.client.order_cancel(orderId)),
                asyncio.create_task(self.client.order_limit(orderId, order))
            ]
        else:
            pass
            
    async def _cancel_order_(self, order, orderId=None) -> asyncio.Task:
        """Initiate cancel order task to client"""
        return asyncio.create_task(self.client.order_cancel(order))

    async def prioritiser(self, target_delta: float) -> None:
        """The main processing func of orders""" 

        delta_diff = target_delta - self.__current_delta__
        
        # --- High latency check --- #
    
        if self.__current_latency__ > 1000: # NOTE: Currently set to >1000ms
            self.logging.warning(f"High latency detected ({self.__current_latency__}ms), cancelling...")
            await self.client.order_cancel_all()

            if self.__current_delta__ != 0:
                side = 0 if self.__current_delta__ > 0 else 1
                qty = self.it.delta_to_position(self.__current_delta__)
                self.logging.info(f"Neutralizing inventory of {'+' if side == 0 else '-'}{qty}...")
                await self.client.order_market((side, qty))

            return None

        # --- Edge inventory check --- #

        if abs(delta_diff) > 0.25:
            side = 1 if delta_diff > 0 else 0
            qty = None # self.inventory._qty_from_delta_(delta_diff/2)
            await self.client.order_market((side, qty))
            return None

        # --- BBA Checks --- #

        tasks = []

        # If current bid is filled, send new
        if not self.current_bba[0]:
            tasks.append(self._limit_order_(self.new_bba[0]))

        # If current ask is filled, send new
        if not self.current_bba[1]:
            tasks.append(self._limit_order_(self.new_bba[1]))

        # If current bid price/qty changed enough, modify accordingly
        if self._bounds_checker_(self.new_bba[0][2], self.current_bba[0][2]) or \
            self._bounds_checker_(self.new_bba[0][1], self.current_bba[0][1], 0.05):
            price = self.new_bba[0][1]
            qty = self.new_bba[0][2]
            tasks.append(self._amend_order_(self.current_bba[0][3], price, qty))

        # If current ask price/qty changed enough, modify accordingly
        if self._bounds_checker_(self.new_bba[1][2], self.current_bba[1][2]) or \
            self._bounds_checker_(self.new_bba[1][1], self.current_bba[1][1], 0.05):
            price = self.new_bba[1][1]
            qty = self.new_bba[1][2]
            tasks.append(self._amend_order_(self.current_bba[1][3], price, qty))
        
        # --- Outer Checks --- #

        for current_outer, new_outer in zip(self.current_outer, self.new_outer):
            pass

    async def update(self, new_orders: Tuple[List, List], target_delta: float) -> None:
        """Feed new orders into system and run prioritiser"""
        self.new_bba = new_orders[0]
        self.new_outer = new_orders[1]
        self.prioritiser(target_delta)
        
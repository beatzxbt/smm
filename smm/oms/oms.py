import asyncio
import numpy as np
from typing import Dict, List, Coroutine, Union

from smm.sharedstate import SmmSharedState


class OrderManagementSystem:
    """
    Written to spec: [https://twitter.com/BeatzXBT/status/1731757053113147524]
    """
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
    
    @property
    def mid(self) -> float:
        return self.ss.data["orderbook"].get_mid()
    
    def find_closest_order(self, new_order: Dict, sensitivity=0.1) -> Dict:
        """
        Find the order with the closest price to the target price and matching side.

        Parameters
        ----------
        orders : dict
            A dictionary of orders with keys 'createTime', 'side', 'price', and 'size'.

        target_price : float
            The target price to which the closest order price should be found.

        target_side : str
            The target side ('buy' or 'sell') to match with the order's side.

        Returns
        -------
        dict
            The order with the closest price to the target price and matching side.
        """
        closest_order = {}
        min_distance = float('inf')

        for current_order in self.ss.data["current_orders"].values():
            if current_order["side"] == new_order["side"]:
                distance = abs(current_order["price"] - new_order["price"])
    
                if distance < min_distance:
                    min_distance = distance
                    closest_order = current_order

        return closest_order

    async def create_order(self, new_order: Dict) -> Coroutine:
        """Format a create order and send to exchange"""
        return await self.ss.exchange.create_order(
            symbol=self.ss.symbol,
            side=new_order["side"], 
            orderType=new_order["orderType"],
            size=new_order["size"], 
            price=new_order["price"]
        )
    
    async def amend_order(self, orderId: Union[int, str], old_order: Dict, new_order: Dict) -> Coroutine:
        """Format an amend order and send to exchange"""
        return await self.ss.exchange.amend_order(
            symbol=self.ss.symbol,
            orderId=orderId, 
            side=old_order["orderId"],
            size=new_order["size"], 
            price=new_order["price"]
        )
            
    async def cancel_order(self, orderId: Union[int, str]) -> Coroutine:
        """Format a cancel order and send to exchange"""
        return await self.ss.exchange.cancel_order(
            symbol=self.ss.symbol,
            orderId=orderId
        )
    
    async def cancel_all_orders(self) -> Coroutine:
        """Format a cancel order and send to exchange"""
        return await self.ss.exchange.cancel_all_orders(
            symbol=self.ss.symbol
        )

    async def update(self, new_orders: List[Dict]) -> None:
        tasks = []
        current_order_count = len(self.ss.data["current_orders"])

        # If network bugs cause overexposure, reset state
        if current_order_count > self.ss.parameters["total_orders"]:
            tasks.append(self.cancel_all_orders_task())
            current_order_count = 0

        for order in new_orders:
            match order["orderType"]:
                # Send any market orders with high priority
                case 1.0: 
                    tasks.append(self.create_order_task(order))

                # Send limit orders if certain criteria are met
                case 0.0:
                    if current_order_count < self.ss.parameters["total_orders"]:
                        tasks.append(self.create_order_task(order))
                        current_order_count += 1

                    else:
                        continue
                        
                case _:
                    await self.ss.logging.error(f"Incorrect orderType encountered in OMS: {order}")
                    raise ValueError(f"Invalid order type: {order['orderType']}")
                
    async def update_simple(self, new_orders: List[Dict]) -> None:
        try:
            await self.cancel_all_orders()
            await asyncio.gather(*[self.create_order(order) for order in new_orders])

        except Exception as e:
            await self.ss.logging.error(f"Order Management System: {e}")
        




import asyncio
import numpy as np
from typing import Dict, List, Union

from smm.sharedstate import SmmSharedState


class OrderManagementSystem:
    """
    Written to spec: [https://twitter.com/BeatzXBT/status/1731757053113147524]
    """
    def __init__(self, ss: SmmSharedState) -> None:
        self.exch = ss.exchange
        self.data = ss.data
        self.params = ss.parameters
    
    @property
    def mid(self) -> float:
        return self.data["orderbook"].get_mid()
    
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

        for current_order in self.data["current_orders"].values():
            if current_order["side"] == new_order["side"]:
                distance = abs(current_order["price"] - new_order["price"])
    
                if distance < min_distance:
                    min_distance = distance
                    closest_order = current_order

        return closest_order

    async def create_order_task(self, new_order: Dict) -> asyncio.Task:
        """Format a create order task and send to exchange"""
        return asyncio.create_task(self.exch.create_order(
            symbol=self.ss.symbol,
            side=new_order["side"], 
            orderType=new_order["orderType"],
            size=new_order["size"], 
            price=new_order["price"]
        ))
    
    async def amend_order_task(self, orderId: Union[int, str], old_order: Dict, new_order: Dict) -> asyncio.Task:
        """Format an amend order task and send to exchange"""
        return asyncio.create_task(self.exch.amend_order(
            symbol=self.ss.symbol,
            orderId=orderId, 
            side=old_order["orderId"],
            size=new_order["size"], 
            price=new_order["price"]
        ))
            
    async def cancel_order_task(self, orderId: Union[int, str]) -> asyncio.Task:
        """Format a cancel order task and send to exchange"""
        return asyncio.create_task(self.exch.cancel_order(
            symbol=self.ss.symbol,
            orderId=orderId
        ))
    
    async def cancel_all_orders_task(self) -> asyncio.Task:
        """Format a cancel order task and send to exchange"""
        return asyncio.create_task(self.exch.cancel_all_orders(
            symbol=self.ss.symbol
        ))

    async def update(self, new_orders: List[Dict]) -> None:
        tasks = []
        current_order_count = len(self.data["current_orders"])

        # If network bugs cause overexposure, reset state
        if current_order_count > self.params["total_orders"]:
            tasks.append(self.cancel_all_orders_task())
            current_order_count = 0

        for order in new_orders:
            match order["orderType"]:
                # Send any market orders with high priority
                case 1.0: 
                    tasks.append(self.create_order_task(order))

                # Send limit orders if certain criteria are met
                case 0.0:
                    if current_order_count < self.params["total_orders"]:
                        tasks.append(self.create_order_task(order))
                        current_order_count += 1

                    else:
                        continue
                        
                case _:
                    await self.ss.logging.error(f"Incorrect orderType encountered in OMS: {order}")
                    raise ValueError(f"Invalid order type: {order["orderType"]}")
                
    async def update_simple(self, new_orders: List[Dict]) -> None:
        tasks = []
        tasks.append(self.cancel_all_orders_task())

        for order in new_orders:
            tasks.append(self.create_order_task(order))

        await asyncio.gather(*tasks)




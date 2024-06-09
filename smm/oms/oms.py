import asyncio
import numpy as np
from typing import Dict, List, Coroutine, Union

from smm.sharedstate import SmmSharedState

class OrderManagementSystem:
    """
    Handles order management functionalities including creating, amending, and canceling orders.

    Attributes
    ----------
    ss : SmmSharedState
        Shared state object containing the necessary data and configurations.

    symbol : str
        Trading symbol for the orders.

    data : dict
        Shared data dictionary containing order and market data.

    exchange : Exchange
        Exchange interface to send orders to.

    prev_intended_orders : list
        List to keep track of previously intended orders.
    """
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
        self.symbol = ss.symbol
        self.data = ss.data
        self.exchange = ss.exchange
        self.prev_intended_orders = []

    async def create_order(self, new_order: Dict) -> Coroutine:
        """
        Format a create order and send to exchange.

        Parameters
        ----------
        new_order : Dict
            Dictionary containing order details.

        Returns
        -------
        Coroutine
            Coroutine for creating the order.
        """
        return await self.exchange.create_order(
            symbol=self.symbol,
            side=new_order["side"], 
            orderType=new_order["orderType"],
            size=new_order["size"], 
            price=new_order["price"],
            clientOrderId=new_order["clientOrderId"]
        )
    
    async def amend_order(self, old_order: Dict, new_order: Dict) -> Coroutine:
        """
        Format an amend order and send to exchange.

        Parameters
        ----------
        old_order : Dict
            Dictionary containing the details of the old order.

        new_order : Dict
            Dictionary containing the details of the new order.

        Returns
        -------
        Coroutine
            Coroutine for amending the order.
        """
        return await self.exchange.amend_order(
            symbol=self.symbol,
            side=old_order["orderId"],
            size=new_order["size"], 
            price=new_order["price"],
            clientOrderId=old_order["clientOrderId"], 
        )
            
    async def cancel_order(self, clientOrderId: Union[int, str]) -> Coroutine:
        """
        Format a cancel order and send to exchange.

        Parameters
        ----------
        clientOrderId : Union[int, str]
            The client order ID of the order to cancel.

        Returns
        -------
        Coroutine
            Coroutine for canceling the order.
        """
        return await self.exchange.cancel_order(
            symbol=self.symbol,
            clientOrderId=clientOrderId
        )
    
    async def cancel_all_orders(self) -> Coroutine:
        """
        Format a cancel order and send to exchange to cancel all orders.

        Returns
        -------
        Coroutine
            Coroutine for canceling all orders.
        """
        return await self.exchange.cancel_all_orders(
            symbol=self.symbol
        )
    
    def find_matched_order(self, new_order: Dict) -> Dict:
        """
        Attempt to find the order with a matching level number.

        Parameters
        ----------
        new_order : Dict
            The new order from the quote generator.  
        
        Returns
        -------
        dict
            The order with the closest price to the target price and matching side.
        """
        new_order_level = new_order["clientOrderId"][:-2]

        for current_order in self.data["orders"]:
            if current_order["clientOrderId"][:-2] == new_order_level:
                return current_order

        return {}

    def is_lost_order(self, new_order: Dict) -> bool:
        """
        If an order was sent from the client but doesn't show up in the orders dict, 
        it is considered lost.

        Parameters
        ----------
        new_order : Dict
            The new order from the quote generator.  

        Returns 
        -------
        bool
            True if the order was lost, False otherwise
        """
        # Implementation needed
        pass

    def is_out_of_bounds(self, old_order: Dict, new_order: Dict, sensitivity: float=0.1) -> bool:
        """
        Check if the new order's price is out of bounds compared to the old order's price.

        Parameters
        ----------
        old_order : Dict
            The old order details.

        new_order : Dict
            The new order details.

        sensitivity : float, optional
            The sensitivity factor for determining out-of-bounds (default is 0.1).

        Returns
        -------
        bool
            True if the new order's price is out of bounds, False otherwise.
        """
        distance_from_mid = abs(old_order["price"] - self.data["orderbook"].get_mid())
        buffer = distance_from_mid * sensitivity
        
        if new_order["price"] > (old_order["price"] + buffer):
            return True
        
        elif new_order["price"] < (old_order["price"] - buffer):
            return True

        else:
            return False

    async def update(self, new_orders: List[Dict]) -> None:
        """
        Update the order book with new orders, canceling and creating orders as necessary.

        Parameters
        ----------
        new_orders : List[Dict]
            List of new orders to be processed.
        """
        try:
            tasks = []

            if len(self.prev_intended_orders) == 0:
                for order in new_orders:
                    tasks.append(self.create_order(order))

                self.prev_intended_orders = new_orders

                return None
            
            # If network delay causes duplicates, remove all duplicate tags
            if len(self.data["orders"]) > self.ss.parameters["total_orders"]:
                active_tags = set()

                for order in self.data["orders"]:
                    tag = order["clientOrderId"][:-2]

                    if tag not in active_tags:
                        active_tags.add(tag)
                    else:
                        tasks.append(self.cancel_order(order))
                
            for order in new_orders:
                match order["orderType"]:
                    # Send any market orders with high priority
                    case 1: 
                        tasks.append(self.create_order(order))

                    # Send limit orders if certain criteria are met
                    case 0:
                        matching_old_order = self.find_matched_order(order)

                        if matching_old_order and self.is_out_of_bounds(matching_old_order, order):
                            tasks.append(self.cancel_order(matching_old_order["clientOrderId"]))
                            tasks.append(self.create_order(order))
                        else:
                            tasks.append(self.create_order(order))

                    case _:
                        raise ValueError(f"Invalid order type: {order['orderType']}")
            
            self.prev_intended_orders = new_orders

        except Exception as e:
            await self.ss.logging.error(f"OMS: {e}")

    async def update_simple(self, new_orders: List[Dict]) -> None:
        """
        Simple update method to cancel all orders and create new ones.

        Parameters
        ----------
        new_orders : List[Dict]
            List of new orders to be processed.
        """
        try:
            await asyncio.gather(*[
                self.cancel_all_orders(), 
                *[self.create_order(order) for order in new_orders]
            ])

        except Exception as e:
            await self.ss.logging.error(f"OMS: {e}")

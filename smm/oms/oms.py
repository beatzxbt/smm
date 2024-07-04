import asyncio
from typing import List

from frameworks.exchange.base.types import OrderType, Order
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
        List to keep track of previously intended state of orders.
    """
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
        self.symbol = ss.symbol
        self.data = ss.data
        self.exchange = ss.exchange

        self.prev_intended_orders: List[Order] = []

    async def create_order(self, new_order: Order) -> asyncio.Task:
        """
        Format a create order and send to exchange.

        Parameters
        ----------
        new_order : Order
            Dictionary containing order details.

        Returns
        -------
        asyncio.Task
            asyncio.Task for creating the order.
        """
        return asyncio.create_task(self.exchange.create_order(new_order))
    
    async def amend_order(self, old_order: Order, new_order: Order) -> asyncio.Task:
        """
        Format an amend order and send to exchange.

        Parameters
        ----------
        old_order : Order
            The old order.

        new_order : Order
            The new order.

        Returns
        -------
        asyncio.Task
            asyncio.Task for amending the order.
        """
        new_order.clientOrderId = old_order.clientOrderId
        return asyncio.create_task(self.exchange.amend_order(new_order))
            
    async def cancel_order(self, old_order: Order) -> asyncio.Task:
        """
        Format a cancel order and send to exchange.

        Parameters
        ----------
        old_order : Order
            The client order ID of the order to cancel.

        Returns
        -------
        asyncio.Task
            asyncio.Task for canceling the order.
        """
        return asyncio.create_task(self.exchange.cancel_order(old_order))
    
    async def cancel_all_orders(self) -> asyncio.Task:
        """
        Format a cancel order and send to exchange to cancel all orders.

        Returns
        -------
        asyncio.Task
            asyncio.Task for canceling all orders.
        """
        return asyncio.create_task(self.exchange.cancel_all_orders(
            symbol=self.symbol
        ))
    
    def find_matched_order(self, new_order: Order) -> Order:
        """
        Attempt to find the order with a matching level number.

        Steps
        -----
        1. Extract the level number from the `clientOrderId` of the `new_order`.
        2. Iterate through the current orders in `self.data["orders"]`.
        3. Compare the level number of each current order with the `new_order` level number.
        4. Return the first matching order found, or an empty Order if no match is found.

        Parameters
        ----------
        new_order : Order
            The new order from the quote generator.  
        
        Returns
        -------
        Order
            The order with the closest price to the target price and matching side.
        """
        new_order_level = new_order.clientOrderId[:-2]

        for current_order in self.data["orders"]:
            if current_order.clientOrderId[:-2] == new_order_level:
                return current_order

        return Order()

    def is_out_of_bounds(self, old_order: Order, new_order: Order, sensitivity: float=0.1) -> bool:
        """
        Check if the new order's price is out of bounds compared to the old order's price.

        Steps
        -----
        1. Calculate the distance from the mid price using the old order's price.
        2. Determine the acceptable price range using the sensitivity factor.
        3. Check if the new order's price is within the acceptable range.
        4. Return True if the price is out of bounds, otherwise return False.

        Parameters
        ----------
        old_order : Order
            The old order.

        new_order : Order
            The new order.

        sensitivity : float, optional
            The sensitivity factor for determining out-of-bounds (default is 0.1 or 10%).

        Returns
        -------
        bool
            True if the new order's price is out of bounds, False otherwise.
        """
        distance_from_mid = abs(old_order.price - self.data["orderbook"].get_mid())
        buffer = distance_from_mid * sensitivity
        
        if new_order.price > (old_order.price + buffer):
            return True
        
        elif new_order.price < (old_order.price - buffer):
            return True

        else:
            return False

    async def update(self, new_orders: List[Order]) -> None:
        """
        Update the order book with new orders, canceling and creating orders as necessary.

        This method processes new orders and updates the existing orders by:
        
        1. Creating new orders if there are no previously intended orders.
        2. Cancelling any duplicate orders that might be created due to network delay.
        3. Processing each new order based on its type (MARKET or LIMIT).
        4. Replacing out-of-bound orders with new orders when necessary.
        
        Steps:
        ------
        1. If there are no previously intended orders, create all new orders:
            a. Iterate over each new order.
            b. Create a task to send the order to the exchange.
        
        2. Handle duplicate orders caused by network delays:
            a. Check if the number of active orders exceeds the allowed total orders.
            b. Identify duplicate tags by checking the client order ID.
            c. Cancel the duplicate orders.
        
        3. Process each new order based on its type:
            a. If the order type is MARKET:
                i. Create a task to send the order to the exchange.
            
            b. If the order type is LIMIT:
                i. Find a matching old order by comparing the client order ID.
                ii. Check if the new order is out of bounds compared to the old order.
                iii. If out of bounds, cancel the old order and create a new order.
                iv. If not out of bounds, create the new order.
        
        Parameters
        ----------
        new_orders : List[Order]
            List of new orders to be processed.
        
        Returns
        -------
        None
        """
        try:
            tasks = []
            
            # Step 2
            if len(self.prev_intended_orders) == 0:
                for order in new_orders:
                    tasks.append(self.create_order(order))
                    await self.ss.logging.debug(f"Sending order: {order}")

                return None
            
            # Step 2
            if len(self.data["orders"]) > self.ss.parameters["total_orders"]:
                active_tags = set()

                for order in self.data["orders"]:
                    tag = str(order.side) + str(order.clientOrderId[:-2])

                    if tag not in active_tags:
                        active_tags.add(tag)
                    else:
                        tasks.append(self.cancel_order(order))
                        await self.ss.logging.debug(f"Cancelling duplicate order: {order}")
            
            # Step 3
            for order in new_orders:
                match order.orderType:
                    case OrderType.MARKET: 
                        tasks.append(self.create_order(order))
                        await self.ss.logging.debug(f"Sending order: {order}")

                    case OrderType.LIMIT:
                        matching_old_order = self.find_matched_order(order)

                        if matching_old_order and self.is_out_of_bounds(matching_old_order, order):
                            tasks.append(self.cancel_order(matching_old_order))
                            tasks.append(self.create_order(order))
                            await self.ss.logging.debug(f"Replacing order: {order}")
                        else:
                            tasks.append(self.create_order(order))
                            await self.ss.logging.debug(f"Sending order: {order}")

                    case _:
                        raise ValueError(f"Invalid order type: {order.orderType}")
            
        except Exception as e:
            await self.ss.logging.error(f"OMS: {e}")

    async def update_simple(self, new_orders: List[Order]) -> None:
        """
        Simple update method to cancel all orders and create new ones.

        Parameters
        ----------
        new_orders : List[Order]
            List of new orders to be processed.
        """
        try:
            await asyncio.gather(*[
                self.cancel_all_orders(), 
                *[self.create_order(order) for order in new_orders]
            ])

        except Exception as e:
            await self.ss.logging.error(f"OMS: {e}")

import asyncio
import aiohttp
import json
import numpy as np

from src.bybit.order.client import Client
from src.bybit.order.types import OrderTypesSpot, OrderTypesFutures


class Order:


    def __init__(self, sharedstate):
        
        self.ss = sharedstate

        self.order_market = OrderTypesFutures(self.ss.bybit_symbol)

        self.api_key = self.ss.api_key
        self.api_secret = self.ss.api_secret
        self.client = Client(self.api_key, self.api_secret)
        self.session = aiohttp.ClientSession()


    async def submit_market(self, order: tuple) -> json:
        """
        {order}: Tuple of struct (side: string, price: float, qty: float)

        Returns a JSON with the orderId & latency
        """

        side = str(order[0])
        qty = str(order[2])

        async with self.session:

            payload = self.order_market.market(side, qty)

            response = await self.client.order(self.session, payload)

            return response


    async def submit_limit(self, order: tuple) -> json:
        """
        {order}: Tuple of struct (side: string, price: float, qty: float)

        Returns a JSON with the orderId & latency
        """

        async with self.session:

            side = str(order[0])
            price = str(order[1])
            qty = str(order[2])

            payload = self.order_market.limit(side, price, qty)

            response = await self.client.order(self.session, payload)

            return response


    async def submit_batch(self, orders: list) -> json:
        """
        {orders}: List containing tuples of struct (side: string, price: float, qty: float) \n

        For optimal order submission, list should be organized in the following order: \n
            -> 5 orders closest to BBA (what wants to be filled faster) \n
            -> 10 orders (if existing) on the side with majority orders \n
            -> Reminder of the orders \n
        """

        async def submit_sessionless_limit(session, order):
            """
            Prevent session from closing without the use of 'async with'
            """

            side = str(order[0])
            price = str(order[1])
            qty = str(order[2])

            payload = self.order_market.limit(side, price, qty)

            response = await self.client.order(session, payload)

            return response

        num_orders = len(orders)
        orders_submitted = 0
        
        async with self.session:

            if num_orders <= 25:
                
                tasks = []

                # These will send the 5 singles at the start \
                for order in orders[:5]:

                    task = asyncio.create_task(submit_sessionless_limit(self.session, order))
                    tasks.append(task)

                    orders_submitted += 1

                bba = await asyncio.gather(*tasks)
                        
                # If there are orders remaining, send them through batch orders \
                if (num_orders - orders_submitted) > 0:

                    overflow = []
                    
                    batches_to_send = int(np.ceil((num_orders-orders_submitted)/10))

                    for i in range(batches_to_send):
                        
                        batch = []

                        for order in orders[5+(10*i):5+(10*(i+1))]:

                            side = str(order[0])
                            price = str(order[1])
                            qty = str(order[2])

                            single_payload = self.order_market.limit(side, price, qty)

                            batch.append(single_payload)
                        
                        batch_payload = {"category": "linear", "request": batch}

                        batch_task = asyncio.create_task(self.client.batch_order(self.session, batch_payload))
                        overflow.append(batch_task)

                    rest = await asyncio.gather(*overflow)


    async def amend(self, order: tuple) -> json:
        """
        {order}: Tuple of struct (orderId: string, price: float, qty: float)

        Returns a JSON with the orderId & latency 
        """
        
        async with self.session:

            payload = self.order_market.amend(order)

            response = await self.client.amend(self.session, payload)

            return response


    async def cancel(self, orderId: str):
        """
        Cancels an order

        Returns a JSON with the orderId & latency 
        """
        
        async with self.session:

            payload = self.order_market.cancel(orderId)

            response = await self.client.cancel(self.session, payload)

            return response


    async def cancel_all(self):
        """
        Cancels all orders

        Returns a JSON with the orderId & latency 
        """
        
        async with self.session:

            payload = self.order_market.cancel_all()

            response = await self.client.cancel_all(self.session, payload)

            return response
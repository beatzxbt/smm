import asyncio
import aiohttp
import json
import numpy as np

from src.exchanges.bybit.order.client import Client
from src.exchanges.bybit.order.types import OrderTypesFutures
from src.exchanges.bybit.order.endpoints import OrderEndpoints

from src.sharedstate import SharedState


class Order:


    def __init__(self, sharedstate: SharedState):
        
        self.ss = sharedstate

        self.order_market = OrderTypesFutures(self.ss.bybit_symbol)

        self.api_key = self.ss.api_key
        self.api_secret = self.ss.api_secret
        self.client = Client(self.api_key, self.api_secret)
        self.session = aiohttp.ClientSession()
        self.endpoints = OrderEndpoints


    async def submit_market(self, order: tuple) -> json:
        """
        {order}: Tuple of struct (side: string, price: float, qty: float)

        Returns a JSON with the orderId & latency
        """

        async with self.session:

            payload = self.order_market.market(order)
            endpoint = self.endpoints.CREATE_ORDER

            response = await self.client.submit(self.session, endpoint, payload)

            return response


    async def submit_limit(self, order: tuple) -> json:
        """
        {order}: Tuple of struct (side: string, price: float, qty: float)

        Returns a JSON with the orderId & latency
        """

        async with self.session:

            payload = self.order_market.limit(order)
            endpoint = self.endpoints.CREATE_ORDER

            response = await self.client.submit(self.session, endpoint, payload)

            return response


    async def submit_batch(self, orders: list) -> json:
        """
        {orders}: List containing tuples of struct (side: string, price: float, qty: float) \n

        For optimal order submission, list should be organized in the following order: \n
            -> 4 orders closest to BBA (what wants to be sent faster) \n
            -> 10 orders (if existing) on the side with majority orders \n
            -> Reminder of the orders \n
        """
        
        single_endpoint = self.endpoints.CREATE_ORDER
        batch_endpoint = self.endpoints.CREATE_BATCH

        async def submit_sessionless_limit(session, order):
            """
            Prevent session from closing without the use of 'async with'
            """

            payload = self.order_market.limit(order)
            response = await self.client.submit(session, single_endpoint, payload)

            return response

        num_orders = len(orders)
        orders_submitted = 0
        
        async with self.session:

            if num_orders <= 24:
                
                tasks = []

                # These will send the 4 singles at the start \
                for order in orders[:4]:

                    task = asyncio.create_task(submit_sessionless_limit(self.session, order))
                    tasks.append(task)

                    orders_submitted += 1

                await asyncio.gather(*tasks)
                        
                # If there are orders remaining, send them through batch orders \
                if (num_orders - orders_submitted) > 0:

                    overflow = []
                    
                    batches_to_send = int(np.ceil((num_orders-orders_submitted)/10))

                    for i in range(batches_to_send):
                        
                        batch = []

                        for order in orders[4+(10*i):4+(10*(i+1))]:

                            single_payload = self.order_market.limit(order)
                            batch.append(single_payload)
                        
                        batch_payload = {"category": "linear", "request": batch}

                        batch_task = asyncio.create_task(self.client.submit(self.session, batch_endpoint, batch_payload))
                        overflow.append(batch_task)

                    await asyncio.gather(*overflow)


    async def amend(self, order: tuple) -> json:
        """
        {order}: Tuple of struct (orderId: string, price: float, qty: float)

        Returns a JSON with the orderId & latency 
        """
        
        async with self.session:

            payload = self.order_market.amend(order)
            endpoint = self.endpoints.AMEND_ORDER

            response = await self.client.submit(self.session, endpoint, payload)

            return response


    async def amend_batch(self, orders: list) -> json:
        """
        {orders}: List containing tuples of struct (orderId: string, price: float, qty: float) \n
        """

        batch_endpoint = self.endpoints.AMEND_BATCH

        async with self.session:
            
            batch = []

            for order in orders:
                payload = self.order_market.amend(order)
                batch.append(payload)
            
            batch_payload = {"category": "linear", "request": batch}

            await self.client.submit(self.session, batch_endpoint, batch_payload)


    async def cancel(self, orderId: str):
        """
        Cancels an order

        Returns a JSON with the orderId & latency 
        """
        
        async with self.session:

            payload = self.order_market.cancel(orderId)
            endpoint = self.endpoints.CANCEL_SINGLE
            
            response = await self.client.submit(self.session, endpoint, payload)

            return response

        
    async def cancel_batch(self, orderIds: list):
        """
        {orderIds}: List containing orderIds \n
        """

        batch_endpoint = self.endpoints.CANCEL_BATCH

        async with self.session:
            
            batch = []

            for id in orderIds:
                payload = self.order_market.cancel(id)
                batch.append(payload)
            
            batch_payload = {"category": "linear", "request": batch}

            await self.client.submit(self.session, batch_endpoint, batch_payload)


    async def cancel_all(self):
        """
        Cancels all orders

        Returns a JSON with the orderId & latency 
        """
        
        async with self.session:

            payload = self.order_market.cancel_all()
            endpoint = self.endpoints.CANCEL_ALL
            
            response = await self.client.submit(self.session, endpoint, payload)

            return response
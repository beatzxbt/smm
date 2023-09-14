
import asyncio
import aiohttp

from src.exchanges.bybit.post.client import BybitPrivatePostClient
from src.exchanges.bybit.endpoints import PrivatePostLinks
from src.exchanges.bybit.post.types import OrderTypesFutures
from src.sharedstate import SharedState


class Order:

    # {order}: Tuple of struct (side: string, price: float, qty: float)

    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.futures = OrderTypesFutures(self.ss.bybit_symbol)
        self.api_key = self.ss.api_key
        self.api_secret = self.ss.api_secret
        self.client = BybitPrivatePostClient(self.api_key, self.api_secret)
        self.endpoints = PrivatePostLinks
        self.session = aiohttp.ClientSession()


    def _order_to_str(self, order) -> tuple[str, ...]:
        return tuple(map(str, order))


    async def _submit(self, endpoint, payload):
        async with self.session:
            return await self.client.submit(self.session, endpoint, payload)


    async def _sessionless_submit(self, endpoint, payload):
        return await self.client.submit(self.session, endpoint, payload)


    async def order_market(self, order: tuple) -> dict | None:
        endpoint = self.endpoints.CREATE_ORDER
        str_order = self._order_to_str(order)
        payload = self.futures.market(str_order)

        return await self._submit(endpoint, payload)


    async def order_limit(self, order: tuple) -> dict | None:
        endpoint = self.endpoints.CREATE_ORDER
        str_order = self._order_to_str(order)
        payload = self.futures.limit(str_order)

        return await self._submit(endpoint, payload)


    async def order_batch(self, orders: list) -> dict | None:
        batch_endpoint = self.endpoints.CREATE_BATCH
        tasks = []

        # Split the orders into chunks of 10
        for i in range(0, len(orders), 10):
            str_orders = [self._order_to_str(order) for order in orders[i:i+10]]
            batch = [self.futures.limit(order) for order in str_orders]
            batch_payload = {"category": "linear", "request": batch}
            task = self._sessionless_submit(batch_endpoint, batch_payload)
            tasks.append(task)

        await asyncio.gather(*tasks)
        await self.session.close()


    async def amend(self, order: tuple) -> dict | None:
        endpoint = self.endpoints.AMEND_ORDER
        str_order = self._order_to_str(order)
        payload = self.futures.amend(str_order)

        return await self._submit(endpoint, payload)


    async def amend_batch(self, orders: list) -> dict | None:
        batch_endpoint = self.endpoints.AMEND_BATCH
        tasks = []

        # Split the orders into chunks of 10
        for i in range(0, len(orders), 10):
            str_orders = [self._order_to_str(order) for order in orders[i:i+10]]
            batch = [self.futures.amend(order) for order in str_orders]
            batch_payload = {"category": "linear", "request": batch}
            task = self._sessionless_submit(batch_endpoint, batch_payload)
            tasks.append(task)

        await asyncio.gather(*tasks)
        await self.session.close()


    async def cancel(self, orderId: str) -> dict | None:
        endpoint = self.endpoints.CANCEL_SINGLE
        payload = self.futures.cancel(orderId)

        return await self._submit(endpoint, payload)


    async def cancel_batch(self, orderIds: list) -> dict | None:
        batch_endpoint = self.endpoints.CANCEL_BATCH
        tasks = []

        # Split the orderIds into chunks of 10
        for i in range(0, len(orderIds), 10):
            batch = [self.futures.cancel(order) for order in orderIds[i:i+10]]
            batch_payload = {"category": "linear", "request": batch}
            task = self._sessionless_submit(batch_endpoint, batch_payload)
            tasks.append(task)

        await asyncio.gather(*tasks)
        await self.session.close()


    async def cancel_all(self) -> dict | None:
        endpoint = self.endpoints.CANCEL_ALL
        payload = self.futures.cancel_all()

        return await self._submit(endpoint, payload)

import asyncio
import aiohttp
from typing import List, Dict, Tuple, Union
from src.exchanges.bybit.post.client import BybitPrivatePostClient
from src.exchanges.bybit.endpoints import PrivatePostLinks
from src.exchanges.bybit.post.types import BybitFormats
from src.sharedstate import SharedState


class Order:
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.key, self.secret = self.ss.api_key, self.ss.api_secret
        self.formats = BybitFormats(self.ss.bybit_symbol)
        self.endpoints = PrivatePostLinks
        self.client = BybitPrivatePostClient(self.ss)
        self.session = aiohttp.ClientSession()

    def _order_to_str_(self, order: List) -> List[str]:
        return list(map(str, order))

    async def _submit_(self, endpoint: str, payload: Dict):
        async with self.session:
            return await self.client.submit(self.session, endpoint, payload)

    async def _sessionless_submit_(self, endpoint: str, payload: Dict):
        return await self.client.submit(self.session, endpoint, payload)

    async def order_market(self, order: Tuple) -> Union[Dict, None]:
        endpoint = self.endpoints.CREATE_ORDER
        side, qty = self._order_to_str_(order)
        payload = self.formats.create_market(side, qty)
        return await self._submit_(endpoint, payload)

    async def order_limit(self, order: Tuple) -> Union[Dict, None]:
        endpoint = self.endpoints.CREATE_ORDER
        side, price, qty = self._order_to_str_(order)
        payload = self.formats.create_limit(side, price, qty)
        return await self._submit_(endpoint, payload)

    async def order_limit_batch(self, orders: List) -> Union[Dict, None]:
        batch_endpoint = self.endpoints.CREATE_BATCH
        tasks = []

        # Split the orders into chunks of 10
        for i in range(0, len(orders), 10):
            orders = [self._order_to_str_(order) for order in orders]
            batch_payload = {
                "category": "linear", 
                "request": [
                    self.formats.create_limit(order[0], order[1], order[2]) 
                    for order in orders[i:i+10]
                ]
            }
            task = self._sessionless_submit_(batch_endpoint, batch_payload)
            tasks.append(task)

        await asyncio.gather(*tasks)
        await self.session.close()

    async def amend(self, order: Tuple) -> Union[Dict, None]:
        endpoint = self.endpoints.AMEND_ORDER
        orderId, price, qty = self._order_to_str_(order)
        payload = self.formats.create_amend(orderId, price, qty)
        return await self._submit_(endpoint, payload)

    async def amend_batch(self, orders: List) -> Union[Dict, None]:
        batch_endpoint = self.endpoints.AMEND_BATCH
        tasks = []

        # Split the orders into chunks of 10
        for i in range(0, len(orders), 10):
            orders = [self._order_to_str_(order) for order in orders]
            batch_payload = {
                "category": "linear", 
                "request": [
                    self.formats.create_amend(order[0], order[1], order[2])
                    for order in orders[i:i+10]
                ]
            }
            task = self._sessionless_submit_(batch_endpoint, batch_payload)
            tasks.append(task)

        await asyncio.gather(*tasks)
        await self.session.close()

    async def cancel(self, orderId: str) -> Union[Dict, None]:
        endpoint = self.endpoints.CANCEL_SINGLE
        payload = self.formats.create_cancel(orderId)
        return await self._submit_(endpoint, payload)

    async def cancel_batch(self, orderIds: List) -> Union[Dict, None]:
        batch_endpoint = self.endpoints.CANCEL_BATCH
        tasks = []

        # Split the orderIds into chunks of 10
        for i in range(0, len(orderIds), 10):
            batch_payload = {
                "category": "linear", 
                "request": [
                    self.formats.create_cancel(orderId)
                    for orderId in orderIds[i:i+10]
                ]
            }
            task = self._sessionless_submit_(batch_endpoint, batch_payload)
            tasks.append(task)

        await asyncio.gather(*tasks)
        await self.session.close()

    async def cancel_all(self) -> Union[Dict, None]:
        endpoint = self.endpoints.CANCEL_ALL
        payload = self.formats.create_cancel_all()
        return await self._submit_(endpoint, payload)
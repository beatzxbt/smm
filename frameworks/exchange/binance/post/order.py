
import asyncio
import aiohttp

from frameworks.exchange.binance.post.client import BinancePrivatePostClient
from frameworks.exchange.binance.endpoints import PrivatePostLinks
from frameworks.exchange.binance.post.types import OrderTypesFutures
from frameworks.sharedstate.private import PrivateDataSharedState

from typing import List, Dict, Tuple


class BinanceOrder:
    """ 
    {order}: Tuple of struct (side: float, price: float, qty: float)
    """

    def __init__(
        self, 
        sharedstate: PrivateDataSharedState, 
        symbol: str
    ) -> None:

        self.client = BinancePrivatePostClient(sharedstate)
        self.futures = OrderTypesFutures(symbol)
        self.endpoints = PrivatePostLinks
        self.session = aiohttp.ClientSession()


    def _map_to_str(self, order: Tuple) -> Tuple[str, ...]:
        return tuple(map(str, order))


    def _set_order_side(self, side: int | float) -> str:
        return "BUY" if side == 1 else "SELL"


    async def _submit(self, endpoint: str, payload: Dict) -> Dict | None:
        return await self.client.submit(self.session, endpoint, payload)


    async def market(self, order: Tuple, tp: float=None) -> Dict | None:
        endpoint = self.endpoints.CREATE
        order[0] = self._set_order_side(order[0])
        str_order = self._map_to_str(order)
        payload = self.futures.market(str_order, tp)

        return await self._submit(endpoint, payload)


    async def limit(self, order: Tuple, tp: float=None) -> Dict | None:
        endpoint = self.endpoints.CREATE
        order[0] = self._set_order_side(order[0])
        str_order = self._map_to_str(order)
        payload = self.futures.limit(str_order, tp)

        return await self._submit(endpoint, payload)


    async def amend(self, order: Tuple, tp: float=None) -> Dict | None:
        endpoint = self.endpoints.CREATE
        order[0] = self._set_order_side(order[0])
        str_order = self._map_to_str(order)
        payload = self.futures.amend(str_order, tp)

        return await self._submit(endpoint, payload)


    async def cancel(self, orderId: str) -> Dict | None:
        endpoint = self.endpoints.CREATE
        payload = self.futures.cancel(orderId)

        return await self._submit(endpoint, payload)


    async def cancel_all(self) -> Dict | None:
        endpoint = self.endpoints.CANCEL_ALL
        payload = self.futures.cancel_all()

        return await self._submit(endpoint, payload)

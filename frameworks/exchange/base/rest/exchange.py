from typing import Dict, Optional, Union, _T
from frameworks.exchange.base.rest.client import Client

class Exchange:
    """
    Base exchange class
    """

    def __init__(self, client: Client, endpoints: Dict, formats: Dict) -> None:
        self.client = client
        self.endpoints = endpoints
        self.format = formats
    
    async def _post_(self, endpoint: str, payload: Dict, rlType: str) -> Union[Dict, None]:
        """Submit a post request to the client"""
        await self.client.post(endpoint, payload)

    async def _get_(self, endpoint: str, payload: Dict, rlType: str) -> Union[Dict, None]:
        """Submit a get request to the client"""
        await self.client.get(endpoint, payload)

    async def post_create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Union[Dict, None]:
        endpoint = self.endpoints["post_create_order"]
        payload = self.format.create_order(symbol, side, type, amount, price, tp)
        return await self._post_(endpoint, payload)

    async def post_amend_order(
        self,
        orderId: str,
        amount: float,
        price: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Union[Dict, None]:
        endpoint = self.endpoints["post_amend_order"]
        payload = self.format.amend_order(orderId, amount, price, tp)
        return await self._post_(endpoint, payload)

    async def post_cancel_order(self, orderId: str) -> Union[Dict, None]:
        endpoint = self.endpoints["post_cancel_order"]
        payload = self.format.cancel_order(orderId)
        return await self._post_(endpoint, payload)

    async def post_cancel_all_orders(self, symbol: str) -> Union[Dict, None]:
        endpoint = self.endpoints["post_cancel_all_orders"]
        payload = self.format.cancel_all_orders(symbol)
        return await self._post_(endpoint, payload)

    async def get_ohlc(self, symbol: str, interval: int) -> Union[Dict, None]:
        endpoint = self.endpoints["get_ohlc"]
        payload = self.format.get_ohlc(symbol, interval)
        return await self._get_(endpoint, payload)

    async def get_trades(self, symbol: str, limit: int) -> Union[Dict, None]:
        endpoint = self.endpoints["get_trades"]
        payload = self.format.get_trades(symbol, limit)
        return await self._get_(endpoint, payload)

    async def get_book(self, symbol: str, limit: int) -> Union[Dict, None]:
        endpoint = self.endpoints["get_book"]
        payload = self.format.get_book(symbol, limit)
        return await self._get_(endpoint, payload)

    async def get_instrument(self, symbol: str) -> Union[Dict, None]:
        endpoint = self.endpoints["get_instrument"]
        payload = self.format.get_instrument(symbol)
        return await self._get_(endpoint, payload)

    async def get_open_orders(self, symbol: str) -> Union[Dict, None]:
        endpoint = self.endpoints["get_open_orders"]
        payload = self.format.get_open_orders(symbol)
        return await self._get_(endpoint, payload)

    async def get_current_position(self, symbol: str) -> Union[Dict, None]:
        endpoint = self.endpoints["get_current_position"]
        payload = self.format.get_current_position(symbol)
        return await self._get_(endpoint, payload)

    async def get_account_info(self) -> Union[Dict, None]:
        endpoint = self.endpoints["get_account_info"]
        payload = self.format.get_account_info()
        return await self._get_(endpoint, payload)

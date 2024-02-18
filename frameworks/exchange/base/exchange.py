from typing import Dict, Optional, Union
from frameworks.exchange.base.client import Client


class Exchange:
    """
    Base exchange class

    Contains only essential functions which likely all strategies
    will use. If additional functions are required (for basic exchange 
    information initialization like tick/lot sizes), these should be 
    added to the inherited class.
    """
    def __init__(self, client: Client, base_endpoint: str, endpoints: Dict, formats: Dict) -> None:
        self.client = client
        self.base_endpoint = base_endpoint
        self.endpoints = endpoints
        self.formats = formats

    async def _send_(
        self, method: str, endpoint: str, payload: Dict
    ) -> Union[Dict, None]:
        """Submit a request to the client"""
        await self.client.send(method, self.base_endpoint+endpoint, payload)

    async def ping(self) -> Union[Dict, None]:
        endpoint, method = self.endpoints["ping"]
        payload = self.formats.ping()
        return await self._send_(method, endpoint, payload)
    
    async def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Union[Dict, None]:
        endpoint, method = self.endpoints["createOrder"]
        payload = self.formats.create_order(symbol, side, type, amount, price, tp)
        return await self._send_(method, endpoint, payload)

    async def amend_order(
        self,
        orderId: str,
        amount: float,
        price: float,
        tp: Optional[float] = None,
    ) -> Union[Dict, None]:
        endpoint, method = self.endpoints["amendOrder"]
        payload = self.formats.amend_order(orderId, amount, price, tp)
        return await self._send_(method, endpoint, payload)

    async def cancel_order(self, orderId: str) -> Union[Dict, None]:
        endpoint, method = self.endpoints["cancelOrder"]
        payload = self.formats.cancel_order(orderId)
        return await self._send_(method, endpoint, payload)

    async def cancel_all_orders(self, symbol: str) -> Union[Dict, None]:
        endpoint, method = self.endpoints["cancelAllOrders"]
        payload = self.formats.cancel_all_orders(symbol)
        return await self._send_(method, endpoint, payload)

    async def ohlcv(self, symbol: str, interval: int) -> Union[Dict, None]:
        endpoint, method = self.endpoints["ohlcv"]
        payload = self.formats.ohlcv(symbol, interval)
        return await self._send_(method, endpoint, payload)

    async def trades(self, symbol: str, limit: int) -> Union[Dict, None]:
        endpoint, method = self.endpoints["trades"]
        payload = self.formats.trades(symbol, limit)
        return await self._send_(method, endpoint, payload)

    async def orderbook(self, symbol: str, limit: int) -> Union[Dict, None]:
        endpoint, method = self.endpoints["orderbook"]
        payload = self.formats.orderbook(symbol, limit)
        return await self._send_(method, endpoint, payload)

    async def open_orders(self, symbol: str) -> Union[Dict, None]:
        endpoint, method = self.endpoints["allOpenOrders"]
        payload = self.formats.open_orders(symbol)
        return await self._send_(method, endpoint, payload)

    async def open_position(self, symbol: str) -> Union[Dict, None]:
        endpoint, method = self.endpoints["currentPosition"]
        payload = self.formats.open_position(symbol)
        return await self._send_(method, endpoint, payload)


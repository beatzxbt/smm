from typing import Dict, Optional

from frameworks.exchange.base.exchange import Exchange
from frameworks.exchange.bybit.endpoints import BybitEndpoints
from frameworks.exchange.bybit.formats import BybitFormats
from frameworks.exchange.bybit.client import BybitClient

class Bybit(Exchange):
    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = BybitClient(self.api_key, self.api_secret)
        self.formats = BybitFormats()
        self.endpoints = BybitEndpoints
        self.base_endpoint = self.endpoints["main1"]
        super().__init__(self.client)

    async def create_order(self, symbol: str, side: str, orderType: float, size: float, price: Optional[float]=None) -> Dict:
        endpoint, method = self.endpoints["createOrder"]
        payload = self.formats.create_order(symbol, side, orderType, size, price)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method,
            payload=payload, 
            signed=False
        )
    
    async def amend_order(self, symbol: str, orderId: int, size: float, price: float) -> Dict:
        endpoint, method = self.endpoints["amendOrder"]
        payload = self.formats.amend_order(orderId, size, price)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method,
            payload=payload, 
            signed=False
        )
    
    async def cancel_order(self, symbol: str, orderId: str) -> Dict:
        endpoint, method = self.endpoints["cancelOrder"]
        payload = self.formats.cancel_order(symbol, orderId)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method,
            payload=payload, 
            signed=False
        )
    
    async def cancel_all_orders(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["cancelAllOrders"]
        payload = self.formats.cancel_all_orders(symbol)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method,
            payload=payload, 
            signed=False
        )

    async def get_orderbook(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["orderbook"]
        params = self.formats.get_orderbook(symbol)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method, 
            params=params
        )
    
    async def get_trades(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["trades"]
        params = self.formats.get_trades(symbol)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method, 
            params=params
        )
    
    async def get_ohlcv(self, symbol: str, interval: int=1) -> Dict:
        endpoint, method = self.endpoints["ohlcv"]
        params = self.formats.get_ohlcv(symbol, interval)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method, 
            params=params
        )
    
    async def get_ticker(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["ticker"]
        params = self.formats.get_ticker(symbol)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method, 
            params=params
        )
    
    async def get_open_orders(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["allOpenOrders"]
        payload = self.formats.get_open_orders(symbol)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method,
            payload=payload
        )
    
    async def get_position(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["positionInfo"]
        payload = self.formats.get_position(symbol)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method,
            payload=payload
        )

    async def get_instrument_info(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["instrumentInfo"]
        params = self.formats.get_instrument_info(symbol)
        return await self.client.request(
            url=self.base_endpoint+endpoint,
            method=method,
            params=params
        )
    
    async def warmup(self) -> None:
        try:
            instrument_data = await self.get_instrument_info(self.symbol)
            
            for instrument in instrument_data["result"]["list"]:
                if instrument["symbol"] != self.symbol:
                    continue

                self.data["tick_size"] = float(instrument["priceFilter"]["tickSize"])
                self.data["lot_size"] = float(instrument["lotSizeFilter"]["qtyStep"])

        except Exception as e:
            await self.logging.error(f"Bybit exchange warmup: {e}")

        finally:
            await self.logging.info(f"Bybit warmup sequence complete.")
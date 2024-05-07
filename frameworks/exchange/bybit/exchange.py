from typing import Any, Dict,Coroutine, Optional

from frameworks.sharedstate import SharedState
from frameworks.exchange.base.exchange import Exchange
from frameworks.exchange.bybit.endpoints import BybitEndpoints
from frameworks.exchange.bybit.formats import BybitFormats
from frameworks.exchange.bybit.client import BybitClient


class Bybit(Exchange):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.client = BybitClient(self.ss.api_key, self.ss.api_secret)
        super().__init__(self.client)

        self.endpoints = BybitEndpoints
        self.formats = BybitFormats()

    async def create_order(self, symbol: str, side: str, orderType: float, size: float, price: Optional[float]=None) -> Dict:
        endpoint, method = self.endpoints["createOrder"]
        payload = self.formats.create_order(symbol, side, orderType, size, price)
        return await self.submit(method, endpoint, payload)
    
    async def amend_order(self, symbol: str, orderId: int, size: float, price: float) -> Dict:
        endpoint, method = self.endpoints["amendOrder"]
        payload = self.formats.amend_order(orderId, size, price)
        return await self.submit(method, endpoint, payload)
    
    async def cancel_order(self, symbol: str, orderId: str) -> Dict:
        endpoint, method = self.endpoints["cancelOrder"]
        payload = self.formats.cancel_order(symbol, orderId)
        return await self.submit(method, endpoint, payload)
    
    async def cancel_all_orders(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["cancelAllOrder"]
        payload = self.formats.cancel_all_orders(symbol)
        return await self.submit(method, endpoint, payload)

    async def current_open_orders(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["allOpenOrders"]
        payload = self.formats.get_open_orders(symbol)
        return await self.submit(method, endpoint, payload)
    
    async def current_position(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["positionInfo"]
        payload = self.formats.get_position(symbol)
        return await self.submit(method, endpoint, payload)
    
    # TODO: Add orderbook, trades, ohlcv, ticker GET calls here
    
    async def instument_info(self, symbol: str) -> Dict:
        endpoint, method = self.endpoints["instumentInfo"]
        payload = self.formats.instrument_info(symbol)
        return await self.submit(method, endpoint, payload)
    
    async def warmup(self) -> None:
        try:
            instrument_data = await self.instument_info(self.ss.symbol)
            
            for instrument in instrument_data:
                if instrument["symbol"] != self.ss.symbol:
                    continue

                self.ss.misc["tick_size"] = float(instrument["priceFilter"]["tickSize"])
                self.ss.misc["lot_size"] = float(instrument["lotSizeFilter"]["qtyStep"])

        except Exception as e:
            self.ss.logging.error(f"Bybit exchange: {e}")

        finally:
            self.websocket.shutdown()
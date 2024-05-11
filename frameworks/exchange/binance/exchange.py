from frameworks.exchange.base.exchange import Exchange
from frameworks.exchange.binance.endpoints import BinanceEndpoints
from frameworks.exchange.binance.formats import BinanceFormats
from frameworks.exchange.binance.client import BinanceClient
from frameworks.sharedstate import SharedState
from typing import Any, Dict,Coroutine, Union, Optional


class Binance(Exchange):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss

        self.client = BinanceClient(self.ss.api_key, self.ss.api_secret)
        super().__init__(self.client)

        self.endpoints = BinanceEndpoints
        self.formats = BinanceFormats()

    async def create_order(self, symbol: str, side: str, type: float, size: float, price: Optional[float]=None) -> Union[Dict, None]:
        endpoint, method = self.endpoints["createOrder"]
        payload = self.formats.create_order(symbol, side, type, size, price)
        return await self.submit(method, endpoint, payload)
    
    async def amend_order(self, symbol: str, side: int, price: float, size: float) -> Union[Dict, None]:
        endpoint, method = self.endpoints["amendOrder"]
        payload = self.formats.amend_order(symbol, side, price, size)
        return await self.submit(method, endpoint, payload)
    
    async def cancel_order(self, symbol: str, orderId: str) -> Union[Dict, None]:
        endpoint, method = self.endpoints["cancelOrder"]
        payload = self.formats.cancel_order(symbol, orderId)
        return await self.submit(method, endpoint, payload)
    
    async def cancel_all_orders(self, symbol: str) -> Union[Dict, None]:
        endpoint, method = self.endpoints["cancelAllOrder"]
        payload = self.formats.cancel_all_orders(symbol)
        return await self.submit(method, endpoint, payload)

    async def exchange_info(self) -> Union[Dict, None]:
        endpoint, method = self.endpoints["exchangeInfo"]
        payload = self.formats.get_exchange_info()
        return await self.submit(method, endpoint, payload)
    
    async def get_listen_key(self) -> Union[Dict, None]:
        endpoint, method = self.endpoints["listenKey"]
        payload = self.formats.get_listen_key()
        return await self.submit(method, endpoint, payload)
    
    async def ping_listen_key(self) -> Union[Dict, None]:
        endpoint, method = self.endpoints["pingListenKey"]
        payload = self.formats.ping_listen_key()
        return await self.submit(method, endpoint, payload)
    
    async def start(self) -> Coroutine:
        try:
            for symbol in (await self.exchange_info())["symbols"]:
                if self.ss.symbol != symbol["symbol"]:
                    continue
                
                for filter in symbol["filters"]:
                    if filter["filterType"] == "PRICE_FILTER":
                        self.ss.misc["tick_size"] = float(filter["tickSize"])
                    elif filter["filterType"] == "LOT_SIZE":
                        self.ss.misc["lot_size"] = float(filter["stepSize"])

            self.websocket.start()

        except Exception as e:
            self.ss.logging.error(f"Binance exchange: {e}")

        finally:
            self.websocket.shutdown()
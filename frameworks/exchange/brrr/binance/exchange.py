from frameworks.exchange.base.exchange import Exchange
from frameworks.exchange.brrr.binance.endpoints import BinanceEndpoints
from frameworks.exchange.brrr.binance.formats import BinanceFormats
from frameworks.exchange.brrr.binance.client import BinanceClient
from frameworks.exchange.brrr.binance.websocket import BinanceWebsocket
from typing import Any, Dict, Union


class Binance(Exchange):
    def __init__(self, market: Dict[str, Any], private: Union[Dict[str, Any], bool]=False) -> None:
        self.market = market
        self.private = private
        self.endpoints = BinanceEndpoints
        self.base_endpoint = self.endpoints["main1"]
        self.formats = BinanceFormats()
        self.client = BinanceClient(self._private_)
        self.websocket = BinanceWebsocket(self.client, self._market_, self._private_)
        super().__init__(self.client, self.base_endpoint, self.endpoints, self.formats)
        self._initialize_()

    @property
    def _market_(self) -> Dict:
        return self.market["binance"]

    @property
    def _private_(self) -> Dict:
        return self.private["binance"]

    async def exchange_info(self) -> Union[Dict, None]:
        endpoint, method = self.endpoints["exchangeInfo"]
        payload = self.formats
        return await self._send_(method, endpoint, payload)
    
    async def listen_key(self, symbol: str) -> Union[Dict, None]:
        endpoint, method = self.endpoints["listenKey"]
        payload = self.formats.listen_key(symbol)
        return await self._send_(method, endpoint, payload)
    
    async def cancel_all_orders(self, symbol: str) -> Union[Dict, None]:
        endpoint, method = self.endpoints["cancelAllOrders"]
        payload = self.formats.cancel_all_orders(symbol)
        return await self._send_(method, endpoint, payload)
    
    async def cancel_all_orders(self, symbol: str) -> Union[Dict, None]:
        endpoint, method = self.endpoints["cancelAllOrders"]
        payload = self.formats.cancel_all_orders(symbol)
        return await self._send_(method, endpoint, payload)

    async def _initialize_(self) -> None:
        """
        Called only from sharedstate._cache_info_(), full docstring found there

        Parameters
        ----------
        symbol : str
            

        Returns
        -------
        None
        """

        await self.ping()

        for ratelimit in (await self.exchange_info())["rateLimits"]:
            if ratelimit["rateLimitType"] != "ORDERS":
                continue

            self._private_["API"]["rateLimits"] = {
                ""
            }

    for symbols in (await self.exchange_info())["symbols"]:
        if symbol != symbols["symbol"]:
            continue
        
        for filter in symbols["filters"]:
            if filter["filterType"] == "PRICE_FILTER":
                self.__market__[symbol]["tickSize"] = filter["tickSize"]
            elif filter["filterType"] == "LOT_SIZE":
                self.__market__[symbol]["lotSize"] = filter["stepSize"]
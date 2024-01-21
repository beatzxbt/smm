import asyncio
from frameworks.exchange.base.rest.exchange import Exchange
from frameworks.exchange.brrrclient.binance.endpoints import BinanceEndpoints
from frameworks.exchange.brrrclient.binance.formats import BinanceFormats
from frameworks.exchange.brrrclient.binance.client import BinanceClient
from frameworks.sharedstate import SharedState
from typing import Dict


class Binance(Exchange):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.endpoints = BinanceEndpoints
        self.formats = BinanceFormats()
        self.client = BinanceClient(self.__private__["API"])
        super().__init__(self.client, self.endpoints, self.formats)

        self._exchange_info_cached_ = False
    
    @property
    def __market__(self) -> Dict:
        return self.ss.market["binance"]

    @property
    def __private__(self) -> Dict:
        return self.ss.private["binance"]

    async def initialize(self, symbol: str) -> None:
        """
        Called only from sharedstate._cache_info_(), full docstring found there

        Parameters
        ----------
        symbol : str
            

        Returns
        -------
        None
        """

        if not self._exchange_info_cached_:
            await self.ping()
            for rl_type in (await self.exchange_info())["rateLimits"]:
                if rl_type != "ORDERS":
                    continue

                self.__private__["API"]
                
            self._exchange_info_cached_ = True

        for symbols in (await self.exchange_info())["symbols"]:
            if symbol != symbols["symbol"]:
                continue
            
            for filter in symbols["filters"]:
                if filter["filterType"] == "PRICE_FILTER":
                    self.__market__[symbol]["tickSize"] = filter["tickSize"]
                elif filter["filterType"] == "LOT_SIZE":
                    self.__market__[symbol]["lotSize"] = filter["stepSize"]
            

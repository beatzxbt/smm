import asyncio
from frameworks.exchange.base.exchange import Exchange
from typing import Dict


class CcxtClient(Exchange):
    """
    Inherits the base exchange class, but doesnt use it.
    Remember to strictly conform with its (base class) functions wholly,
    meaning the function names, arguments, and execution are all the same.
    """

    def __init__(self, market: Dict, private: Dict) -> None:
        self.market, self.private = market, private
        self.ccxt_rest = None 
        self._exchange_info_cached_ = False
    
    @property
    def __market__(self) -> Dict:
        return self.ss.market["binance"]

    @property
    def __private__(self) -> Dict:
        return self.ss.private["binance"]

    def load(self, exchange: str):
        self.ccxt_client = 

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
            

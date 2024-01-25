from frameworks.exchange.base.rest.exchange import Exchange
from frameworks.exchange.brrr.hyperliquid.endpoints import HyperliquidEndpoints
from frameworks.exchange.brrr.hyperliquid.formats import HyperliquidFormats
from frameworks.exchange.brrr.hyperliquid.client import HyperliquidClient
from typing import Dict, Optional, Union


class Hyperliquid(Exchange):
    """
    Abnormal exchange, overwrite all required exchange funcs
    """

    def __init__(self, market: Dict, private: Dict) -> None:
        self.market, self.private = market, private
        self.endpoints = HyperliquidEndpoints
        self.formats = HyperliquidFormats()
        self.client = HyperliquidClient(self.__private__["API"])
        super().__init__(self.client, self.endpoints, self.formats)
        self.set_base_endpoint(self.endpoints["main1"])

        self._exchange_info_cached_ = False

    @property
    def __market__(self) -> Dict:
        return self.market["hyperliquid"]

    @property
    def __private__(self) -> Dict:
        return self.private["hyperliquid"]

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

        for symbols in (await self.exchange_info())["universe"]:
            if symbol != symbols["symbol"]:
                continue
            
            for filter in symbols["filters"]:
                if filter["filterType"] == "PRICE_FILTER":
                    self.__market__[symbol]["tickSize"] = filter["tickSize"]
                elif filter["filterType"] == "LOT_SIZE":
                    self.__market__[symbol]["lotSize"] = filter["stepSize"]
    
    async def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Union[Dict, None]:
        endpoint, method = self.endpoints["exchange"]
        payload = self.formats.create_order(symbol, side, type, amount, price, tp)
        return await self._send_(method, endpoint, payload)
import asyncio
from typing import Dict, List, Tuple, Union, Optional
from frameworks.tools.logger import Logger
from frameworks.exchange.base.stream import WebsocketStream
from frameworks.exchange.ccxt.handlers import (
    CcxtBbaHandler, CcxtOrderbookHandler, CcxtTradesHandler,
    CcxtOhlcvHandler, CcxtTickerHandler, CcxtOrdersHandler, 
    CcxtPositionHandler
)


class CcxtWs(WebsocketStream):
    def __init__(self, market: Dict, private: Dict, flag: Optional[bool]=False) -> None:
        self.market, self.private = market, private
        self.flag = flag
        self.logging = Logger
        self.key = self.__private__["API"]["key"]
        self.secret = self.__private__["API"]["secret"]

    @property
    def __market__(self) -> Dict:
        return self.ss.market["binance"]

    @property
    def __private__(self) -> Dict:
        return self.ss.private["binance"]

    def _public_stream_(self) -> Union[Dict, Exception]:
        async def bba(self) -> None:
            while True:
                async with self.lock:
                    try:
                        limit = self.ss.order_book_limits.get(self.exchange, 5)

                        bba_update = await self._pro_client_.watch_order_book(
                            symbol=self.symbol, limit=limit
                        )

                        self.handler_map["bba"](bba_update)
                        self.fp.calculate()

                    except Exception as e:
                        self.logging.error(f"Error on BBA feed: {e}")

        async def ticker(self) -> None:
            while True:
                async with self.lock:
                    try:
                        ticker_update = await self._pro_client_.fetch_funding_rate(
                            symbol=self.symbol
                        )

                        self.handler_map["ticker"](ticker_update)
                        self.fp.calculate()

                except Exception as e:
                    self.logging.error(f"Error on Ticker feed: {e}")

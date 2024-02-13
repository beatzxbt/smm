import asyncio
import ccxt.pro as ccxtpro
from typing import Dict, List, Tuple, Union, Optional
from frameworks.tools.logger import Logger
from frameworks.exchange.base.websocket import WebsocketStream
from frameworks.exchange.ccxt.handlers import (
    CcxtBbaHandler, CcxtOrderbookHandler, CcxtTradesHandler,
    CcxtOhlcvHandler, CcxtTickerHandler, CcxtOrdersHandler, 
    CcxtPositionHandler
)


class CcxtWs(WebsocketStream):
    def __init__(self, exchange: str, market: Dict, private: Dict, flag: Optional[bool]=False) -> None:
        self.exchange = exchange
        self.market, self.private = market, private
        self.flag = flag
        self.key = self.__private__["API"]["key"]
        self.secret = self.__private__["API"]["secret"]
        self.logging = Logger
        self.client = self.initialize(self.exchange)
    
    def initialize(self, exchange: ccxtpro.Exchange) -> ccxtpro.Exchange:
        try:
            ws_client = getattr(ccxtpro, exchange)
            ws_client({
                "apiKey": self.key, 
                "secret": self.secret, 
                "options": {"defaultType": "swap"}
            })
            return ws_client
        
        except Exception as e:
            self.logging.error(f"Error initializing {exchange}: {e}")
            raise e

    @property
    def __market__(self) -> Dict:
        return self.market[self.exchange]

    @property
    def __private__(self) -> Dict:
        return self.private[self.exchange]

    async def _public_stream_(self) -> List[asyncio.Task]:
        symbols = self.__market__.keys()
        return [
            asyncio.create_task(self._bba_streams_(symbols)),
            asyncio.create_task(self._book_streams_(symbols)),
            asyncio.create_task(self._trades_streams_(symbols)),
            asyncio.create_task(self._ohlcv_streams_(symbols)),
            asyncio.create_task(self._ticker_streams_(symbols))
        ]

    async def _bba_streams_(self, symbols) -> None:
        levels = 1
        while True:
            try:
                recv = await self.client.watch_order_book_for_symbols(symbols, levels)
                self.handler_map["bba"](recv)

            except Exception as e:
                self.logging.error(f"Error on BBA feed: {e}")

    async def _book_streams_(self, symbols) -> None:
        levels = 500
        while True:
            try:
                recv = await self.client.watch_order_book_for_symbols(symbols, levels)
                self.handler_map["book"](recv)
            except Exception as e:
                self.logging.error(f"Error on BBA feed: {e}")

    async def _trades_streams_(self, symbols) -> None:
        while True:
            try:
                recv = await self.client.watch_trades_for_symbols(symbols)
                self.handler_map["trades"](recv)
            except Exception as e:
                self.logging.error(f"Error on BBA feed: {e}")

    async def _ohlcv_streams_(self, symbols) -> None:
        symbols_w_tfs = None # TODO: Construct list
        while True:
            try:
                recv = await self.client.watch_ohlcv_for_symbols(symbols_w_tfs)
                self.handler_map["ohlcv"](recv)

            except Exception as e:
                self.logging.error(f"Error on BBA feed: {e}")

    async def _ticker_streams_(self, symbols) -> None:
        while True:
            try:
                recv = await self.client.watch_tickers(symbols)
                self.handler_map["ticker"](recv)
            except Exception as e:
                self.logging.error(f"Error on Ticker feed: {e}")

import asyncio
from typing import Any, Dict, List, Union

from frameworks.exchange.base.websocket import WebsocketStream
from frameworks.exchange.binance.exchange import Binance
from frameworks.exchange.binance.endpoints import BinanceEndpoints
from frameworks.exchange.binance.handlers.orderbook import BinanceOrderbookHandler
from frameworks.exchange.binance.handlers.trades import BinanceTradesHandler
from frameworks.exchange.binance.handlers.markprice import BinanceTickerHandler
from frameworks.exchange.binance.handlers.ohlcv import BinanceOhlcvHandler
from frameworks.exchange.binance.handlers.orders import BinanceOrdersHandler
from frameworks.exchange.binance.handlers.position import BinancePositionHandler
from frameworks.sharedstate import SharedState


class BinanceWebsocket(WebsocketStream):
    def __init__(self, ss: SharedState, exch: Binance) -> None:     
        self.ss = ss   
        self.exch = exch

        super().__init__(self.ss.logging)

        self.endpoints = BinanceEndpoints

        self.public_handler_map = {
            "depthUpdate": BinanceOrderbookHandler(self.ss).process,
            "trade": BinanceTradesHandler(self.ss).process,
            "kline": BinanceOhlcvHandler(self.ss).process,
            "markPriceUpdate": BinanceTickerHandler(self.ss).process,
        }
        self.public_handler_map["bookTicker"] = self.public_handler_map["depthUpdate"]

        self.private_handler_map = {
            "ORDER_TRADE_UPDATE": BinanceOrdersHandler(self.ss).process,
            "ACCOUNT_UPDATE": BinancePositionHandler(self.ss).process,
            "listenKeyExpired": None # TODO: Add custom handler here
        }
    
    def _gen_public_stream_info_(self, symbols: List[str]) -> str:
        url = self.endpoints["pub_ws"] + "/stream?streams="
        for symbol in symbols:
            url += f"{symbol}@trade/{symbol}@depth@100ms/"
            url += f"{symbol}@markPrice@1s/{symbol}@kline_1m"
        return url[:-1]
    
    def _public_stream_handler_(self, recv: Dict) -> None:
        self.public_handler_map[recv["data"]["e"]](recv["data"])
        
    async def public_stream(self, symbols: List[str]):
        try:
            url = self._gen_public_stream_info_(symbols)
            await self.start_public_ws(url, self._public_stream_handler_)
        except Exception as e:
            self.logging.error(f"Binance Public Websocket: {e}")

    async def _gen_private_stream_info_(self) -> str:
        self.listen_key = self.exch.get_listen_key()
        url = self.endpoints["priv_ws"] + "/ws/" + self.listen_key
        return url[:-1]
    
    async def _ping_listen_key_(self) -> None:
        try:
            self.listen_key = self.exch.ping_listen_key()

            # if isinstance()
        except Exception as e:
            raise e

    def _private_stream_handler_(self, recv: Dict) -> None:
        self.private_handler_map[recv["data"]["e"]](recv["data"])
        
    async def private_stream(self):
        try:
            url = self._gen_private_stream_info_()
            await self.start_private_ws(url, self._private_stream_handler_)
        except Exception as e:
            self.logging.error(f"Binance Private Ws: {e}")
    
    async def start(self, symbol: str) -> None:
        await asyncio.gather(*[
            asyncio.create_task(self.public_stream(symbol)),
            asyncio.create_task(self.private_stream())
        ])
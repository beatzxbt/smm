import asyncio
from typing import Any, Dict, List, Union

from frameworks.tools.logger import Logger
from frameworks.exchange.base.websocket import WebsocketStream
from frameworks.exchange.base.client import Client
from frameworks.exchange.brrr.binance.endpoints import BinanceEndpoints
from frameworks.exchange.brrr.binance.handlers.bba import BinanceBbaHandler
from frameworks.exchange.brrr.binance.handlers.book import BinanceOrderbookHandler
from frameworks.exchange.brrr.binance.handlers.trades import BinanceTradesHandler
from frameworks.exchange.brrr.binance.handlers.ticker import BinanceTickerHandler
from frameworks.exchange.brrr.binance.handlers.markprice import BinanceMarkPriceHandler
from frameworks.exchange.brrr.binance.handlers.ohlcv import BinanceOhlcvHandler
from frameworks.exchange.brrr.binance.handlers.orders import BinanceOrdersHandler
from frameworks.exchange.brrr.binance.handlers.position import BinancePositionHandler


class BinanceWebsocket(WebsocketStream):
    def __init__(self, client: Client, market: Dict[str, Any], private: Union[Dict[str, Any], bool]=False) -> None:        
        self.client = client
        self.market = market
        self.private = private 
        self.logging = Logger
        super().__init__(isinstance(self.private, Dict))
        self._set_internal_logger_(self.logging)
        self.endpoints = BinanceEndpoints

        self.public_handler_map = {
            "bookTicker": BinanceBbaHandler(self._market).process,
            "depthUpdate": BinanceOrderbookHandler(self._market).process,
            "trade": BinanceTradesHandler(self._market).process,
            "kline": BinanceOhlcvHandler(self._market).process,
            "markPriceUpdate": BinanceMarkPriceHandler(self._market).process,
            "24hrMiniTicker": BinanceTickerHandler(self._market).process,
        }

        self.private_handler_map = {
            "ORDER_TRADE_UPDATE": BinanceOrdersHandler(self._private_).process,
            "ACCOUNT_UPDATE": BinancePositionHandler(self._private_).process,
            "listenKeyExpired": None # TODO: Add custom handler here
        }
    
    @property
    def _market_(self) -> Dict:
        return self.market["binance"]

    @property
    def _private_(self) -> Dict:
        return self.private["binance"]
    
    def _gen_public_stream_info_(self, symbols: List[str]) -> str:
        url = self.endpoints["pub_ws"] + "/stream?streams="
        for symbol in symbols:
            url += f"{symbol}@trade/{symbol}@depth@100ms/{symbol}@bookTicker/"
            url += f"{symbol}@markPrice@1s/{symbol}@kline_1m/{symbol}@miniTicker/"
        return url[:-1]
    
    def _public_stream_handler_(self, recv: Dict) -> None:
        self.public_handler_map[recv["data"]["e"]](recv["data"])
        
    async def _public_stream_(self, symbols: List[str]):
        try:
            url = self._gen_public_stream_info_(symbols)
            await self.public_stream(url, self._public_stream_handler_)
        except Exception as e:
            self.logging.error(f"binance public ws: {e}")

    async def _gen_private_stream_info_(self) -> str:
        listen_key = self.client.listen_key()
        url = self.endpoints["priv_ws"] + "/ws/" + listen_key
        return url[:-1]
    
    def _private_stream_handler_(self, recv: Dict) -> None:
        data = recv["data"]
        self.private_handler_map[data["e"]](data)
        
    async def _private_stream_(self):
        try:
            url = self._gen_private_stream_info_()
            await self.private_stream(url, self._private_stream_handler_)
        except Exception as e:
            self.logging.error(f"binance private ws: {e}")
    
    async def start(self, symbols: List[str]) -> None:
        tasks = [asyncio.create_task(self._public_stream_(symbols))]
        if isinstance(self.private, Dict):
            tasks.append(asyncio.create_task(self._private_stream_()))
        await asyncio.gather(*tasks)
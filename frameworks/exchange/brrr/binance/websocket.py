import asyncio
import hashlib
import hmac
from typing import Dict, List, Tuple, Union, Optional

from frameworks.tools.logger import Logger
from frameworks.exchange.base.ws.stream import WebsocketStream
from frameworks.exchange.brrr.binance.endpoints import BinanceEndpoints
from frameworks.exchange.brrr.binance.handlers import (
    BinanceBbaHandler, BinanceOrderbookHandler, BinanceTradesHandler,
    BinanceOhlcvHandler, BinanceTickerHandler, BinanceOrdersHandler, 
    BinancePositionHandler
)


class BinanceWs(WebsocketStream):
    def __init__(self, market: Dict, private: Union[Dict, None], flag: Optional[bool]=False) -> None:
        self.market = market
        self.private = private
        self.flag = flag
        self.logging = Logger
        super().__init__(self.logging)
        self.key = self.__private__["API"]["key"]
        self.secret = self.__private__["API"]["secret"]
        self.pub = BinanceEndpoints["pub_ws"]
        self.priv = BinanceEndpoints["priv_ws"]

        public_url, public_handlers = self._build_public_request_()
        private_url, private_handlers = self._build_private_request_()
        
    @property
    def __market__(self) -> Dict:
        return self.market["binance"]

    @property
    def __private__(self) -> Dict:
        return self.private["binance"]

    def _build_public_request_(self, ohlcv_interval: int=1) -> Tuple[str, Dict]:
        """
        Construct a url with required symbols & topics
        to be used in filling respective market data dicts

        Parameters
        ----------
        ohlcv_interval : int
            default value = 1

        Returns
        -------
        Tuple[str, Dict]
        """
        handler_map = {}
        url = self.pub + "/stream?streams="

        for symbol in self.__market__.keys():
            url += f"{symbol}@trade/"
            handler_map[f"{symbol}@trade"] = BinanceTradesHandler(self.__market__)

            url += f"{symbol}@depth@100ms/"
            handler_map[f"{symbol}@depth@100ms"] = BinanceOrderbookHandler(self.__market__)

            url += f"{symbol}@bookTicker/"
            handler_map[f"{symbol}@bookTicker"] = BinanceBbaHandler(self.__market__)

            url += f"{symbol}@kline_{ohlcv_interval}/"
            handler_map[f"{symbol}@kline_{ohlcv_interval}"] = BinanceOhlcvHandler(self.__market__)

        return url[:-1], handler_map

    def _build_public_handler_map_(self, topic_list: List[str]) -> Dict:
        handler_map = {}

        for topic in topic_list:
            if "book" in topic:
                handler_map[topic] = BinanceBbaHandler(self.__market__)

            elif "depth" in topic:
                handler_map[topic] = BinanceOrderbookHandler(self.__market__)

            elif "trades" in topic:
                handler_map[topic] = BinanceTradesHandler(self.__market__)

            elif "ohlcv" in topic:
                handler_map[topic] = BinanceOhlcvHandler(self.__market__)

            elif "ticker" in topic:
                handler_map[topic] = BinanceTickerHandler(self.__market__)

        return handler_map

    def _build_private_request_(self, symbols: List[str], topics: List[str], **kwargs) -> Tuple:
        """
        Construct a string with required symbols & topics
        to be used in initiating the websocket stream

        Parameters
        ----------
        symbols : List[str]
            All symbols to start market data streams with

        topics : List[str]
            All types of streams initiated, ex; trades, orderbook, etc

        kwargs : Dict
            Valid kwargs are:
                -> interval (for ohlcv stream, must be called)

        Returns
        -------
        Tuple[str, List[str]]
        """
        topic_list = []
        url = self.pub + "/stream?streams="

        for symbol in symbols:
            for topic in topics:
                if topic == "trade":
                    stream = "{}@trade/".format(symbol)

                elif topic == "orderbook":
                    stream = "{}@depth@100ms/".format(symbol)

                elif topic == "bba":
                    stream = "{}@bookTicker/".format(symbol)

                elif topic == "ohlcv" and kwargs["interval"] is not None:
                    stream = "{}@kline_{}/".format(symbol, kwargs["interval"])

                url += stream
                topic_list.append(stream[:-1])

        return url[:-1], topic_list

    def _build_private_handler_map_(self, topic_list: List[str]) -> Dict:
        handler_map = {}

        for topic in topic_list:
            if "book" in topic:
                handler_map[topic] = BinanceBbaHandler(self.__market__)

            elif "depth" in topic:
                handler_map[topic] = BinanceOrderbookHandler(self.__market__)

            elif "trades" in topic:
                handler_map[topic] = BinanceTradesHandler(self.__market__)

            elif "ohlcv" in topic:
                handler_map[topic] = BinanceOhlcvHandler(self.__market__)

            elif "ticker" in topic:
                handler_map[topic] = BinanceTickerHandler(self.__market__)

    def _sign_(self, payload: str) -> Dict:
        """SHA-256 signing logic"""
        _ = self.update_timestamp()  # NOTE: Updates self.timestamp
        hash_signature = hmac.new(
            self.secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        self._cached_header_["timestamp"] = self.timestamp
        self._cached_header_["signature"] = hash_signature
        return self._cached_header_
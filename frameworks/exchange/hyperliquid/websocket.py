import asyncio
import hashlib
import hmac
from typing import Dict, List, Tuple, Union

from frameworks.sharedstate import SharedState
from frameworks.exchange.base.websocket import WebsocketStream
from frameworks.exchange.brrr.hyperliquid.endpoints import HyperliquidEndpoints
from frameworks.exchange.brrr.hyperliquid.handlers import (
    HyperliquidBbaHandler, HyperliquidOrderbookHandler, HyperliquidTradesHandler,
    HyperliquidOhlcvHandler, HyperliquidTickerHandler, HyperliquidOrdersHandler, 
    HyperliquidPositionHandler
)


class HyperliquidWs(WebsocketStream):
    def __init__(self, ss: SharedState, private: bool=False) -> None:
        self.ss = ss
        self.private = private
        self.logging = self.ss.logging
        super().__init__(self.logging)
        
        self.pub = HyperliquidEndpoints["pub_ws"]
        self.handler_map = {
            "bba": HyperliquidBbaHandler(self.__market__),
            "book": HyperliquidOrderbookHandler(self.__market__),
            "trades": HyperliquidTradesHandler(self.__market__),
            "ohlcv": HyperliquidOhlcvHandler(self.__market__),
            "ticker": HyperliquidTickerHandler(self.__market__)
        }

        if self.private:
            self.priv = HyperliquidEndpoints["priv_ws"] # NOTE: We can put pub/priv streams on this
            self.key = self.__private__["API"]["key"]
            self.secret = self.__private__["API"]["secret"]
            self.handler_map["orders"] = HyperliquidOrdersHandler(self.__private__)
            self.handler_map["position"] = HyperliquidPositionHandler(self.__private__)

    @property
    def __market__(self) -> Dict:
        return self.ss.market["binance"]

    @property
    def __private__(self) -> Dict:
        return self.ss.private["binance"]

    def _build_request_(self, symbols: List[str], topics: List[str], **kwargs) -> Tuple:
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

    def _sign_(self, payload: str) -> Dict:
        """SHA-256 signing logic"""
        _ = self.update_timestamp()  # NOTE: Updates self.timestamp
        hash_signature = hmac.new(
            self.secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        self._cached_header_["timestamp"] = self.timestamp
        self._cached_header_["signature"] = hash_signature
        return self._cached_header_
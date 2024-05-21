import asyncio
import hmac
import hashlib
from typing import Tuple, Dict, List, Union

from frameworks.tools.logging import time_ms
from frameworks.exchange.base.websocket import WebsocketStream
from frameworks.exchange.bybit.exchange import Bybit
from frameworks.exchange.bybit.endpoints import BybitEndpoints
from frameworks.exchange.bybit.handlers.orderbook import BybitOrderbookHandler
from frameworks.exchange.bybit.handlers.trades import BybitTradesHandler
from frameworks.exchange.bybit.handlers.ticker import BybitTickerHandler
from frameworks.exchange.bybit.handlers.ohlcv import BybitOhlcvHandler
from frameworks.exchange.bybit.handlers.orders import BybitOrdersHandler
from frameworks.exchange.bybit.handlers.position import BybitPositionHandler


class BybitWebsocket(WebsocketStream):
    """
    Handles Websocket connections and data management for Bybit.

    Parameters
    ----------
    ss : SharedState
        A shared memory space containing data, configurations & logging.

    exch : Bybit
        An instance of the Bybit exchange API wrapper.

    Attributes
    ----------
    public_handler_map : dict
        Maps public stream topics to their respective handlers.

    private_handler_map : dict
        Maps private stream topics to their respective handlers.

    Methods
    -------
    start()
        Starts all necessary tasks for managing Websocket streams.
    """
    def __init__(self, exch: Bybit) -> None:     
        super().__init__()
        self.exch = exch
        self.endpoints = BybitEndpoints

    def create_handlers(self) -> None:
        self.public_handler_map = {
            "orderbook": BybitOrderbookHandler(self.data),
            "publicTrade": BybitTradesHandler(self.data),
            "kline": BybitOhlcvHandler(self.data),
            "tickers": BybitTickerHandler(self.data),
        }

        self.private_handler_map = {
            "order": BybitOrdersHandler(self.data, self.symbol),
            "position": BybitPositionHandler(self.data, self.symbol)
        }

    async def refresh_orderbook_data(self, timer: int=600) -> None:
        while True:
            orderbook_data = await self.exch.get_orderbook(self.symbol)
            self.public_handler_map["orderbook"].refresh(orderbook_data)
            await asyncio.sleep(timer)

    async def refresh_trades_data(self, timer: int=600) -> None:
        while True:
            trades_data = await self.exch.get_trades(self.symbol)
            self.public_handler_map["publicTrade"].refresh(trades_data)
            await asyncio.sleep(timer)

    async def refresh_ohlcv_data(self, timer: int=600) -> None:
        while True:
            ohlcv_data = await self.exch.get_ohlcv(self.symbol)
            self.public_handler_map["kline"].refresh(ohlcv_data)
            await asyncio.sleep(timer)

    async def refresh_ticker_data(self, timer: int=600) -> None:
        while True:
            ticker_data = await self.exch.get_ticker(self.symbol)
            self.public_handler_map["tickers"].refresh(ticker_data)
            await asyncio.sleep(timer)
    
    def public_stream_sub(self) -> Tuple[str, List[Dict]]:
        request = [{
            "op": "subscribe", 
            "args": [
                f"publicTrade.{self.symbol}",
                f"tickers.{self.symbol}",
                f"orderbook.500.{self.symbol}",
                f"kline.1.{self.symbol}",
            ]
        }]
        return (self.endpoints["pub_ws"], request)
    
    async def public_stream_handler(self, recv: Dict) -> None:
        try:
            topic = recv["topic"].split(".")[0]
            self.public_handler_map[topic].process(recv)

        except KeyError as ke:
            if "success" not in recv:
                raise ke
            
        except Exception as e:
            await self.logging.error(f"Error with Bybit public ws handler: {e}")

    def private_stream_sub(self) -> Tuple[str, List[Dict]]:
        expiry_time = str(time_ms() + 5000)

        signature = hmac.new(
            key=self.exch.api_secret.encode(),
            msg=f"GET/realtime{expiry_time}".encode(),
            digestmod=hashlib.sha256,
        )

        auth_msg = {
            "op": "auth",
            "args": [self.exch.api_key, expiry_time, signature.hexdigest()],
        }

        sub_msg = {
            "op": "subscribe", 
            "args": [
                "position",
                "execution",
                "order",
                "wallet"
        ]}

        url = self.endpoints["priv_ws"]

        return (url, [auth_msg, sub_msg])
    
    async def private_stream_handler(self, recv: Dict) -> None:
        try:
            self.private_handler_map[recv["topic"]].process(recv)

        except KeyError as ke:
            if "success" not in recv:
                raise ke
            
        except Exception as e:
            await self.logging.error(f"Error with Bybit public ws handler: {e}")
    
    async def start_public_stream(self) -> None:
        """
        Initializes and starts the public Websocket stream.
        """
        try:
            url, requests = self.public_stream_sub()
            await self.start_public_ws(url, self.public_stream_handler, requests)
        except Exception as e:
            await self.logging.error(f"Bybit Public Ws: {e}")

    async def start_private_stream(self):
        """
        Initializes and starts the private Websocket stream.
        """
        try:
            url, requests = self.private_stream_sub()
            await self.start_private_ws(url, self.private_stream_handler, requests)
        except Exception as e:
            await self.logging.error(f"Bybit Private Ws: {e}")
    
    async def start(self) -> None:
        """
        Starts all necessary asynchronous tasks for Websocket stream management and data refreshing.
        """
        self.create_handlers()
        await asyncio.gather(*[
            asyncio.create_task(self.refresh_orderbook_data()),
            asyncio.create_task(self.refresh_trades_data()),
            asyncio.create_task(self.refresh_ohlcv_data()),
            asyncio.create_task(self.refresh_ticker_data()),
            asyncio.create_task(self.start_public_stream()),
            asyncio.create_task(self.start_private_stream()),
        ])
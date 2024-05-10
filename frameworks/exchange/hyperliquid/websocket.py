import asyncio
from typing import Tuple, Dict, List, Union

from frameworks.sharedstate import SharedState
from frameworks.exchange.base.websocket import WebsocketStream
from frameworks.exchange.hyperliquid.exchange import Hyperliquid
from frameworks.exchange.hyperliquid.endpoints import HyperliquidEndpoints
from frameworks.exchange.hyperliquid.handlers.orderbook import HyperliquidOrderbookHandler
from frameworks.exchange.hyperliquid.handlers.trades import HyperliquidTradesHandler
from frameworks.exchange.hyperliquid.handlers.ohlcv import HyperliquidOhlcvHandler
from frameworks.exchange.hyperliquid.handlers.orders import HyperliquidOrdersHandler
from frameworks.exchange.hyperliquid.handlers.web2data import HyperliquidWeb2DataHandler


class HyperliquidWebsocket(WebsocketStream):
    """
    Handles Websocket connections and data management for Hyperliquid.

    Parameters
    ----------
    ss : SharedState
        A shared memory space containing data, configurations & logging.

    exch : Hyperliquid
        An instance of the Hyperliquid exchange API wrapper.

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
    def __init__(self, ss: SharedState, exch: Hyperliquid) -> None:     
        self.ss = ss   
        self.exch = exch

        super().__init__(self.ss.logging)

        self.endpoints = HyperliquidEndpoints

        self.public_handler_map = {
            "l2book": HyperliquidOrderbookHandler(self.ss),
            "trades": HyperliquidTradesHandler(self.ss),
            "candle": HyperliquidOhlcvHandler(self.ss),
            "userHistoricalOrders": HyperliquidOrdersHandler(self.ss),
            "web2data": HyperliquidWeb2DataHandler(self.ss)
        }

        self.private_handler_map = {}   # NOTE: Not needed as all data is public!

    async def refresh_orderbook_data(self, timer: int=600) -> None:
        while True:
            orderbook_data = await self.exch.get_orderbook(self.ss.symbol)
            if "result" in orderbook_data:
                self.public_handler_map["l2book"].initialize(orderbook_data)
            await asyncio.sleep(timer)

    async def refresh_trades_data(self, timer: int=600) -> None:
        while True:
            trades_data = await self.exch.get_trades(self.ss.symbol)
            if "result" in trades_data:
                self.public_handler_map["trades"].initialize(trades_data)
            await asyncio.sleep(timer)

    async def refresh_ohlcv_data(self, timer: int=600) -> None:
        while True:
            ohlcv_data = await self.exch.get_ohlcv(self.ss.symbol)
            if "result" in ohlcv_data:
                self.public_handler_map["candle"].initialize(ohlcv_data)
            await asyncio.sleep(timer)

    async def refresh_ticker_data(self, timer: int=600) -> None:
        while True:
            ticker_data = await self.exch.get_ticker(self.ss.symbol)
            if "result" in ticker_data:
                self.public_handler_map["web2data"].ticker.initialize(ticker_data)
            await asyncio.sleep(timer)
    
    def public_stream_sub(self) -> Tuple[str, List[Dict]]:
        subs = [
            {"type": "trades", "coin": self.ss.symbol},
            {"type": "l2Book", "coin": self.ss.symbol},
            {"type": "candle", "coin": self.ss.symbol, "interval": "1m"},
            {"type": "webData2", "user": self.ss.api_key},
            {"type": "userHistoricalOrders", "user": self.ss.api_key},
        ]

        request = [{"op": "subscribe", "subscription": sub} for sub in subs]

        return (self.endpoints["pub_ws"], request)
    
    async def public_stream_handler(self, recv: Dict) -> None:
        try:
            topic = recv["channel"]
            self.public_handler_map[topic].process(recv)

        except KeyError as ke:
            if topic != "subscriptionResponse":
                raise ke
            
        except Exception as e:
            await self.logging.error(f"Error with hyperliquid public ws handler: {e}")

    async def private_stream_sub(self) -> Tuple[str, List[Dict]]:
        pass
    
    async def private_stream_handler(self, recv: Dict) -> None:
        pass
    
    async def start_public_stream(self) -> None:
        """
        Initializes and starts the public Websocket stream.
        """
        url, request = await self.public_stream_sub()
        await self.start_public_ws(url, self.public_stream_handler, request)

    async def start_private_stream(self):
        """
        Initializes and starts the private Websocket stream.
        """
        pass
    
    async def start(self) -> None:
        """
        Starts all necessary asynchronous tasks for Websocket stream management and data refreshing.
        """
        await asyncio.gather(*[
            asyncio.create_task(self.refresh_orderbook_data()),
            asyncio.create_task(self.refresh_trades_data()),
            asyncio.create_task(self.refresh_ohlcv_data()),
            asyncio.create_task(self.refresh_ticker_data()),
            asyncio.create_task(self.start_public_stream())
        ])
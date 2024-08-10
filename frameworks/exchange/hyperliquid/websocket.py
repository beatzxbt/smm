import asyncio
from typing import Tuple, Dict, List, Union

from frameworks.exchange.base.websocket import WebsocketStream
from frameworks.exchange.hyperliquid.exchange import Hyperliquid
from frameworks.exchange.hyperliquid.endpoints import HyperliquidEndpoints
from frameworks.exchange.hyperliquid.ws_handlers.orderbook import HyperliquidOrderbookHandler
from frameworks.exchange.hyperliquid.ws_handlers.trades import HyperliquidTradesHandler
from frameworks.exchange.hyperliquid.ws_handlers.ohlcv import HyperliquidOhlcvHandler
from frameworks.exchange.hyperliquid.ws_handlers.orders import HyperliquidOrdersHandler
from frameworks.exchange.hyperliquid.ws_handlers.web2data import HyperliquidWeb2DataHandler


class HyperliquidWebsocket(WebsocketStream):
    """
    Handles Websocket connections and data management for Hyperliquid.
    """

    def __init__(self, exch: Hyperliquid) -> None:
        super().__init__()
        self.exch = exch
        self.endpoints = HyperliquidEndpoints()

    def create_handlers(self) -> None:
        self.public_handler_map = {
            "l2book": HyperliquidOrderbookHandler(self.data),
            "trades": HyperliquidTradesHandler(self.data),
            "candle": HyperliquidOhlcvHandler(self.data),
            "userHistoricalOrders": HyperliquidOrdersHandler(self.data),
            "web2data": HyperliquidWeb2DataHandler(self.data)
        }

        self.private_handler_map = {}   # NOTE: Not needed as all data is public!

    async def refresh_orderbook_data(self, timer: int = 600) -> None:
        while True:
            orderbook_data = await self.exch.get_orderbook(self.symbol)
            self.public_handler_map["l2book"].refresh(orderbook_data)
            await asyncio.sleep(timer)

    async def refresh_trades_data(self, timer: int = 600) -> None:
        while True:
            trades_data = await self.exch.get_trades(self.symbol)
            self.public_handler_map["trades"].refresh(trades_data)
            await asyncio.sleep(timer)

    async def refresh_ohlcv_data(self, timer: int = 600) -> None:
        while True:
            ohlcv_data = await self.exch.get_ohlcv(self.symbol)
            self.public_handler_map["candle"].refresh(ohlcv_data)
            await asyncio.sleep(timer)

    async def refresh_ticker_data(self, timer: int = 600) -> None:
        while True:
            ticker_data = await self.exch.get_ticker(self.symbol)
            self.public_handler_map["web2data"].refresh(ticker_data)
            await asyncio.sleep(timer)
    
    def public_stream_sub(self) -> Tuple[str, List[Dict]]:
        subs = [
            {"type": "trades", "coin": self.symbol},
            {"type": "l2Book", "coin": self.symbol},
            {"type": "candle", "coin": self.symbol, "interval": "1m"},
            {"type": "webData2", "user": self.exch.api_key},
            {"type": "userHistoricalOrders", "user": self.exch.api_key},
        ]

        request = [{"op": "subscribe", "subscription": sub} for sub in subs]

        return (self.endpoints.public_ws.url, request)
    
    async def public_stream_handler(self, recv: Dict) -> None:
        try:
            topic = recv["channel"]
            self.public_handler_map[topic].process(recv)

        except KeyError as ke:
            if topic != "subscriptionResponse":
                raise ke
            
        except Exception as e:
            await self.logging.error(f"Error with Hyperliquid public ws handler: {e}")

    async def private_stream_sub(self) -> Tuple[str, List[Dict]]:
        pass
    
    async def private_stream_handler(self, recv: Dict) -> None:
        pass
    
    async def start_public_stream(self) -> None:
        url, request = await self.public_stream_sub()
        await self.start_public_ws(url, self.public_stream_handler, request)

    async def start_private_stream(self):
        pass
    
    async def start(self) -> None:
        self.create_handlers()
        await asyncio.gather(
            self.refresh_orderbook_data(),
            self.refresh_trades_data(),
            self.refresh_ohlcv_data(),
            self.refresh_ticker_data(),
            self.start_public_stream()
        )
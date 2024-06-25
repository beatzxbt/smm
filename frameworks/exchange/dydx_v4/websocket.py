import asyncio
from typing import Tuple, Dict, List

from frameworks.exchange.base.websocket import WebsocketStream
from frameworks.exchange.dydx_v4.exchange import Dydx
from frameworks.exchange.dydx_v4.endpoints import DydxEndpoints
from frameworks.exchange.dydx_v4.handlers.orderbook import DydxOrderbookHandler
from frameworks.exchange.dydx_v4.handlers.trades import DydxTradesHandler
from frameworks.exchange.dydx_v4.handlers.ticker import DydxTickerHandler
from frameworks.exchange.dydx_v4.handlers.ohlcv import DydxOhlcvHandler
from frameworks.exchange.dydx_v4.handlers.subaccounts import DydxSubaccountsHandler


class DydxWebsocket(WebsocketStream):
    """
    Handles Websocket connections and data management for Dydx.
    """

    def __init__(self, exch: Dydx) -> None:
        super().__init__()
        self.exch = exch
        self.endpoints = DydxEndpoints()

    def create_handlers(self) -> None:
        self.public_handler_map = {
            "v4_orderbook": DydxOrderbookHandler(self.data),
            "v4_trades": DydxTradesHandler(self.data),
            "v4_candles": DydxOhlcvHandler(self.data),
            "v4_markets": DydxTickerHandler(self.data),
            "v4_subaccounts": DydxSubaccountsHandler(self.data),
        }

        self.private_handler_map = {}

    async def refresh_orderbook_data(self, timer: int = 600) -> None:
        while True:
            orderbook_data = await self.exch.get_orderbook(self.symbol)
            self.public_handler_map["v4_orderbook"].refresh(orderbook_data)
            await asyncio.sleep(timer)

    async def refresh_trades_data(self, timer: int = 600) -> None:
        while True:
            trades_data = await self.exch.get_trades(self.symbol)
            self.public_handler_map["v4_trades"].refresh(trades_data)
            await asyncio.sleep(timer)

    async def refresh_ohlcv_data(self, timer: int = 1) -> None:
        # Due to missing candlestick websocket feeds, this sync is 
        # set to 1s updates rather than the normal 10min updates
        # to compensate for the missing realtime data feeds.
        #
        # TODO: Follow up with dev team to add this (& document it).

        while True:
            ohlcv_data = await self.exch.get_ohlcv(self.symbol)
            self.public_handler_map["v4_candles"].refresh(ohlcv_data)
            await asyncio.sleep(timer)

    async def refresh_ticker_data(self, timer: int = 600) -> None:
        while True:
            ticker_data = await self.exch.get_ticker(self.symbol)
            self.public_handler_map["v4_markets"].refresh(ticker_data)
            await asyncio.sleep(timer)

    def public_stream_sub(self) -> Tuple[str, List[Dict]]:
        requests = []

        requests.append({
            "type": "subscribe",
            "channel": "v4_subaccounts",
            "id": f"{self.exch.api_key}/{self.exch.api_secret}"
        })

        requests.append({
            "type": "subscribe",
            "channel": "v4_orderbook",
            "id": f"{self.symbol}"
        })

        requests.append({
            "type": "subscribe",
            "channel": "v4_trades",
            "id": f"{self.symbol}"
        })

        # requests.append({
        #     "type": "subscribe",
        #     "channel": "v4_candles",
        #     "id": f"{self.symbol}"
        # })

        requests.append({
            "type": "subscribe",
            "channel": "v4_markets"
        })
            
        return (self.endpoints.public_ws.url, requests)

    async def public_stream_handler(self, recv: Dict) -> None:
        try:
            topic = recv["channel"]
            self.public_handler_map[topic].process(recv)

        except KeyError as ke:
            raise ke
        
        except Exception as e:
            await self.logging.error(f"Error with Dydx public ws handler: {e}")

    def private_stream_sub(self) -> Tuple[str, List[Dict]]:
        pass

    async def private_stream_handler(self, recv: Dict) -> None:
        pass

    async def start_public_stream(self) -> None:
        """
        Initializes and starts the public Websocket stream.
        """
        try:
            url, requests = self.public_stream_sub()
            await self.start_public_ws(url, self.public_stream_handler, requests)
        except Exception as e:
            await self.logging.error(f"Dydx Public Ws: {e}")

    async def start(self) -> None:
        self.create_handlers()
        await asyncio.gather(
            self.refresh_orderbook_data(),
            self.refresh_trades_data(),
            self.refresh_ohlcv_data(),
            self.refresh_ticker_data(),
            self.start_public_stream(),
        )

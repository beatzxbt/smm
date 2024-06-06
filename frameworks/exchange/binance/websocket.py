import asyncio
import hmac
import hashlib
from typing import Tuple, Dict, List, Any

from frameworks.tools.logging import time_ms
from frameworks.exchange.base.websocket import WebsocketStream
from frameworks.exchange.binance.exchange import Binance
from frameworks.exchange.binance.endpoints import BinanceEndpoints
from frameworks.exchange.binance.handlers.orderbook import BinanceOrderbookHandler
from frameworks.exchange.binance.handlers.trades import BinanceTradesHandler
from frameworks.exchange.binance.handlers.markprice import BinanceTickerHandler
from frameworks.exchange.binance.handlers.ohlcv import BinanceOhlcvHandler
from frameworks.exchange.binance.handlers.orders import BinanceOrdersHandler
from frameworks.exchange.binance.handlers.position import BinancePositionHandler


class BinanceWebsocket(WebsocketStream):
    """
    Handles Websocket connections and data management for Binance.
    """

    def __init__(self, exch: Binance) -> None:
        super().__init__()
        self.exch = exch
        self.endpoints = BinanceEndpoints()

    def create_handlers(self) -> None:
        self.public_handler_map = {
            "depthUpdate": BinanceOrderbookHandler(self.data),
            "trade": BinanceTradesHandler(self.data),
            "kline": BinanceOhlcvHandler(self.data),
            "markPriceUpdate": BinanceTickerHandler(self.data),
        }
        self.public_handler_map["bookTicker"] = self.public_handler_map["depthUpdate"]

        self.private_handler_map = {
            "ORDER_TRADE_UPDATE": BinanceOrdersHandler(self.data, self.symbol),
            "ACCOUNT_UPDATE": BinancePositionHandler(self.data, self.symbol),
        }

    async def refresh_orderbook_data(self, timer: int = 600) -> None:
        while True:
            orderbook_data = await self.exch.get_orderbook(self.symbol)
            self.public_handler_map["depthUpdate"].refresh(orderbook_data)
            await asyncio.sleep(timer)

    async def refresh_trades_data(self, timer: int = 600) -> None:
        while True:
            trades_data = await self.exch.get_trades(self.symbol)
            self.public_handler_map["trade"].refresh(trades_data)
            await asyncio.sleep(timer)

    async def refresh_ohlcv_data(self, timer: int = 600) -> None:
        while True:
            ohlcv_data = await self.exch.get_ohlcv(self.symbol, "1m")
            self.public_handler_map["kline"].refresh(ohlcv_data)
            await asyncio.sleep(timer)

    async def refresh_ticker_data(self, timer: int = 600) -> None:
        while True:
            ticker_data = await self.exch.get_ticker(self.symbol)
            self.public_handler_map["markPriceUpdate"].refresh(ticker_data)
            await asyncio.sleep(timer)

    def public_stream_sub(self) -> Tuple[str, List[Dict[str, Any]]]:
        request = [
            {
                "method": "SUBSCRIBE",
                "params": [
                    f"{self.symbol.lower()}@trade",
                    f"{self.symbol.lower()}@depth@100ms",
                    f"{self.symbol.lower()}@markPrice@1s",
                    f"{self.symbol.lower()}@kline_1m",
                ],
                "id": 1,
            }
        ]
        return (self.endpoints.public_ws.url, request)

    async def public_stream_handler(self, recv: Dict[str, Any]) -> None:
        try:
            self.public_handler_map[recv["e"]].process(recv)

        except KeyError as ke:
            if "id" not in recv:
                raise ke

        except Exception as e:
            await self.logging.error(f"Error with Binance public ws handler: {e}")

    async def private_stream_sub(self) -> Tuple[str, List[Dict[str, Any]]]:
        listen_key_data = await self.exch.get_listen_key()
        listen_key = listen_key_data["listenKey"]
        url = self.endpoints.private_ws.url + "/ws/" + listen_key
        return (url, [])

    async def private_stream_handler(self, recv: Dict[str, Any]) -> None:
        try:
            self.private_handler_map[recv["e"]].process(recv)

        except KeyError as ke:
            if "listenKey" not in recv:
                raise ke

        except Exception as e:
            await self.logging.error(f"Error with Binance private ws handler: {e}")

    async def ping_listen_key(self, timer: int = 1800) -> None:
        while True:
            try:
                await asyncio.sleep(timer)
                await self.exch.ping_listen_key()

            except Exception as e:
                await self.logging.error(f"Error with Binance listen key ping: {e}")
                raise e

    async def start_public_stream(self) -> None:
        """
        Initializes and starts the public Websocket stream.
        """
        try:
            url, requests = self.public_stream_sub()
            await self.start_public_ws(url, self.public_stream_handler, requests)
        except Exception as e:
            await self.logging.error(f"Binance Public Ws: {e}")

    async def start_private_stream(self) -> None:
        """
        Initializes and starts the private Websocket stream.
        """
        try:
            url, requests = await self.private_stream_sub()
            await self.start_private_ws(url, self.private_stream_handler, requests)
        except Exception as e:
            await self.logging.error(f"Binance Private Ws: {e}")

    async def start(self) -> None:
        """
        Starts all necessary asynchronous tasks for Websocket stream management and data refreshing.
        """
        self.create_handlers()
        await asyncio.gather(
            self.refresh_orderbook_data(),
            self.refresh_trades_data(),
            self.refresh_ohlcv_data(),
            self.refresh_ticker_data(),
            self.start_public_stream(),
            self.start_private_stream(),
            self.ping_listen_key(),
        )

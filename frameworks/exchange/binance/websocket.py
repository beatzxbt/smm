import asyncio
from typing import Any, Dict, List, Tuple, Union

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
    def __init__(self, exch: Binance) -> None:
        super().__init__()
        self.exch = exch
        self.endpoints = BinanceEndpoints

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
            "listenKeyExpired": None,  # TODO: Add custom handler here
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
            ohlcv_data = await self.exch.get_ohlcv(self.symbol, 1)
            self.public_handler_map["kline"].refresh(ohlcv_data)
            await asyncio.sleep(timer)

    async def refresh_ticker_data(self, timer: int = 600) -> None:
        while True:
            ticker_data = await self.exch.get_ticker(self.symbol)
            self.public_handler_map["markPriceUpdate"].refresh(ticker_data)
            await asyncio.sleep(timer)

    def public_stream_sub(self):
        request = [
            {
                "id": 1,
                "method": "subscribe",
                "params": [
                    f"{self.symbol}@trade",
                    f"{self.symbol}@depth@100ms",
                    f"{self.symbol}@markPrice@1s",
                    f"{self.symbol}@kline_1m",
                ],
            }
        ]
        return (self.endpoints["pub_ws"], request)

    async def public_stream_handler(self, recv: Dict):
        try:
            topic = recv["data"]["e"]
            self.public_handler_map[topic].process(recv)

        except KeyError as ke:
            if "id" not in recv:
                raise ke

        except Exception as e:
            await self.logging.error(f"Error with binance public ws handler: {e}")

    async def private_stream_sub(self) -> Tuple[str, List[Dict]]:
        listen_key = (self.exch.get_listen_key())["listenKey"]
        url = self.endpoints["priv_ws"] + "/ws/" + listen_key
        return (url, [])

    async def private_stream_handler(self, recv: Dict):
        try:
            topic = recv["e"]
            self.private_handler_map[topic].process(recv)

        except KeyError as ke:
            if "listenKey" not in recv:
                raise ke

        except Exception as e:
            await self.logging.error(f"Error with binance private ws handler: {e}")

    async def ping_listen_key(self, timer=900) -> None:
        while True:
            try:
                await asyncio.sleep(timer)

                listen_key = await self.exch.ping_listen_key()
                # TODO: Add error handling here for code -1125
                # TODO: Refer to https://binance-docs.github.io/apidocs/futures/en/#keepalive-user-data-stream-user_stream

            except Exception as e:
                await self.logging.error(f"Error with binance private ws key ping: {e}")
                raise e

    async def start_public_stream(self) -> None:
        """
        Initializes and starts the public Websocket stream.
        """
        url, requests = await self.public_stream_sub()
        await self.start_public_ws(url, self.public_stream_handler, requests)

    async def start_private_stream(self):
        """
        Initializes and starts the private Websocket stream.
        """
        try:
            url, requests = await self.private_stream_sub()
            await self.start_private_ws(url, self.private_stream_handler, requests)
        except Exception as e:
            self.logging.error(f"Bybit Private Ws: {e}")

    async def start(self) -> None:
        """
        Starts all necessary asynchronous tasks for Websocket stream management and data refreshing.
        """
        await asyncio.gather(
            *[
                asyncio.create_task(self.refresh_orderbook_data()),
                asyncio.create_task(self.refresh_trades_data()),
                asyncio.create_task(self.refresh_ohlcv_data()),
                asyncio.create_task(self.refresh_ticker_data()),
                asyncio.create_task(self.start_public_stream()),
                asyncio.create_task(self.start_private_stream()),
                asyncio.create_task(self.ping_listen_key()),
            ]
        )

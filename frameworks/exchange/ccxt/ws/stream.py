import asyncio
from typing import Dict, Tuple, Coroutine
from frameworks.sharedstate import SharedState
from frameworks.exchange.ccxt.ws.handlers.bba import bba_handler
from frameworks.exchange.ccxt.ws.handlers.orderbook import orderbook_handler
from frameworks.exchange.ccxt.ws.handlers.ticker import ticker_handler
from frameworks.exchange.ccxt.ws.handlers.trades import trades_handler
from frameworks.exchange.ccxt.ws.handlers.ohlcv import ohlcv_handler


class CcxtWebsocketStream:
    """Given the exchange, symbol, start market/private data feeds"""
    
    def __init__(self, ss: SharedState, pair: Tuple[str, str], private: bool=False) -> None:
        self.ss = ss
        self.exchange, self.symbol = pair
        self.private = private
        self.logging = self.ss.logging

        self.ws_handler_map = {
            "bba": bba_handler,
            "orderbook": orderbook_handler,
            "trades": trades_handler,
            "ohlcv": ohlcv_handler,
            "ticker": ticker_handler,
        }

    def __market__(self) -> Dict:
        return self.ss.market[self.exchange][self.symbol]

    def __private__(self) -> Dict:
        return self.ss.private[self.exchange][self.symbol]

    async def bba(self) -> Coroutine:
        while True:
            try:
                recv = await self.ss.pro_client.watch_order_book(
                    symbol=self.symbol, 
                    limit=1
                )
                self.ws_handler_map.get("bba")(recv, self.__market__)

            except Exception as e:
                self.logging.error(f"{(self.exchange, self.pair)} bba stream: {e}")
                raise e

    async def orderbook(self) -> Coroutine:
        while True:
            try:
                recv = await self.ss.pro_client.watch_order_book(
                    symbol=self.symbol, 
                    limit=self.__market__["orderbook"].size
                )
                self.ws_handler_map.get("orderbook")(recv, self.__market__)

            except Exception as e:
                self.logging.error(f"{(self.exchange, self.pair)} orderbook stream: {e}")
                raise e

    async def trades(self) -> Coroutine:
        while True:
            try:
                recv = await self.ss.pro_client.watch_trades(symbol=self.symbol)
                self.ws_handler_map.get("trades")(recv, self.__market__)

            except Exception as e:
                self.logging.error(e)
                raise e

    async def ticker(self) -> float:
        while True:
            try:
                recv = await self.ss.pro_client.watch_ticker(symbol=self.symbol)
                self.ws_handler_map.get("ticker")(recv, self.__market__)

            except Exception as e:
                self.logging.error(e)
                raise e

    async def position(self) -> float:
        while True:
            try:
                recv = await self.ss.pro_client.watch_positions([self.symbol])
                self.ws_handler_map.get("position")(recv, self.__private__)

                self.ss.private_data[self.symbol]["position"] = float(position_update[0]["info"]["size"])

            except Exception as e:
                self.logging.error(e)
                raise e

    async def orders(self) -> float:
        while True:
            try:
                recv = await self.ss.pro_client.watch_orderss([self.symbol])
                self.ws_handler_map.get("orders")(recv, self.__private__)

            except Exception as e:
                self.logging.error(e)
                raise e

    async def execution(self) -> float:
        while True:
            try:
                balance_update = await self.ss.pro_client.watch_executions()
                # Add balance processing here

            except Exception as e:
                self.logging.error(e)
                raise e

    async def watch(self) -> None:
        await asyncio.gather(
            asyncio.create_task(self.bba()),
            asyncio.create_task(self.trades()),
            asyncio.create_task(self.ticker()),
            asyncio.create_task(self.position()),
            asyncio.create_task(self.balance()),
        )

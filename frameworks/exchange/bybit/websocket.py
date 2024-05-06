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
from frameworks.sharedstate import SharedState


class BybitWebsocket(WebsocketStream):
    def __init__(self, ss: SharedState, exch: Bybit) -> None:     
        self.ss = ss   
        self.exch = exch

        super().__init__(self.ss.logging)

        self.endpoints = BybitEndpoints

        self.public_handler_map = {
            "orderbook": BybitOrderbookHandler(self.ss).process,
            "publicTrade": BybitTradesHandler(self.ss).process,
            "kline": BybitOhlcvHandler(self.ss).process,
            "tickers": BybitTickerHandler(self.ss).process,
        }

        self.private_handler_map = {
            "order": BybitOrdersHandler(self.ss).process,
            "position": BybitPositionHandler(self.ss).process
        }
    
    def public_stream_sub(self) -> Tuple[str, List[Dict]]:
        request = [{
            "op": "subscribe", 
            "args": [
                f"publicTrade.{self.ss.symbol.upper()}",
                f"tickers.{self.ss.symbol.upper()}",
                f"orderbook.500.{self.ss.symbol.upper()}",
                f"kline.1.{self.ss.symbol.upper()}",
            ]
        }]
        return (self.endpoints["pub_ws"], request)
    
    async def public_stream_handler(self, recv: Dict) -> None:
        try:
            topic = recv["topic"].split(".")[0]
            self.public_handler_map[topic](recv)

        except KeyError as ke:
            if "success" not in recv:
                raise ke
            
        except Exception as e:
            await self.logging.error(f"Error with bybit public ws handler: {e}")

    async def start_public_stream(self) -> None:
        url, request = await self.public_stream_sub()
        await self.start_public_ws(url, self.public_stream_handler, request)

    async def private_stream_sub(self) -> Tuple[str, str, str]:
        expiry_time = str(time_ms() + 5000)

        signature = hmac.new(
            key=self.ss.api_secret.encode(),
            msg=f"GET/realtime{expiry_time}".encode(),
            digestmod=hashlib.sha256,
        )

        auth_msg = {
            "op": "auth",
            "args": [self.ss.api_key, expiry_time, signature.hexdigest()],
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

        return (url, auth_msg, sub_msg)
    
    async def private_stream_handler(self, recv: Dict) -> None:
        try:
            self.private_handler_map[recv["topic"]](recv)

        except KeyError as ke:
            if "success" not in recv:
                raise ke
            
        except Exception as e:
            await self.logging.error(f"Error with bybit public ws handler: {e}")
        
    async def start_private_stream(self):
        try:
            url, auth_msg, sub_msg = await self.private_stream_sub()
            await self.start_private_ws(url, self.private_stream_handler, [auth_msg, sub_msg])
        except Exception as e:
            self.logging.error(f"Bybit Private Ws: {e}")
    
    async def start(self) -> None:
        await asyncio.gather(*[
            asyncio.create_task(self.start_public_stream()),
            asyncio.create_task(self.start_private_stream())
        ])

import asyncio
import orjson
import websockets

from frameworks.tools.logging.logger import Logger
from frameworks.exchange.bybit.get.private import BybitPrivateGet
from frameworks.exchange.bybit.endpoints import WsStreamLinks
from frameworks.exchange.bybit.websockets.handlers.execution import BybitExecutionHandler
from frameworks.exchange.bybit.websockets.handlers.order import BybitOrderHandler
from frameworks.exchange.bybit.websockets.handlers.position import BybitPositionHandler
from frameworks.exchange.bybit.websockets.handlers.wallet import BybitWalletHandler
from frameworks.exchange.bybit.websockets.private import BybitPrivateWsInit
from frameworks.sharedstate.private import PrivateDataSharedState


class BybitPrivateStream:


    def __init__(self, sharedstate: PrivateDataSharedState, symbol: str) -> None:
        self.pdss = sharedstate
        self.symbol = symbol
        self.bybit = self.pdss.bybit[symbol]

        self.logging = Logger()

        self.private_ws = BybitPrivateWsInit(
            api_key=self.bybit["API"]["key"], 
            api_secret=self.bybit["API"]["secret"]
        )

        self.private_client = BybitPrivateGet(
            sharedstate=self.pdss,
            symbol=self.symbol, 
        )

        self.ws_req, self.ws_topics = self.private_ws.multi_stream_request(
            topics=["Position", "Execution", "Order", "Wallet"]
        )

        # Create a dictionary to map topics to handlers
        self.topic_handler_map = {
            self.ws_topics[0]: BybitPositionHandler(self.pdss, self.symbol).update,
            self.ws_topics[1]: BybitExecutionHandler(self.pdss, self.symbol).update,
            self.ws_topics[2]: BybitOrderHandler(self.pdss, self.symbol).update,
            self.ws_topics[3]: BybitWalletHandler(self.pdss, self.symbol).update
        }


    async def _open_orders_sync(self) -> None:
        """
        Sync the current orders every 15s  
        """
        while True:
            recv = await self.private_client.open_orders()
            BybitOrderHandler(self.pdss, self.symbol).sync(recv)
            await asyncio.sleep(15)


    async def _current_position_sync(self) -> None:
        """
        Sync the current position & stats every 15s 
        """
        while True:
            recv = await self.private_client.current_position()
            BybitPositionHandler(self.pdss, self.symbol).sync(recv)
            await asyncio.sleep(15)


    async def _wallet_info_sync(self) -> None:
        """
        Sync the wallet information every 15s 
        """
        while True:
            recv = await self.private_client.wallet_info()
            BybitWalletHandler(self.pdss, self.symbol).sync(recv)
            await asyncio.sleep(15)


    async def _stream(self) -> None:
        async for websocket in websockets.connect(WsStreamLinks.COMBINED_PRIVATE_STREAM):
            self.logging.info(f"Subscribed to BYBIT {self.ws_topics} websocket feeds...")

            try:
                await websocket.send(self.private_ws.auth())
                await websocket.send(self.ws_req)

                while True:
                    recv = orjson.loads(await websocket.recv())

                    if "success" in recv:
                        continue

                    handler_cls = self.topic_handler_map.get(recv["topic"])

                    if handler_cls:
                        handler_cls(recv["data"])

            except websockets.ConnectionClosed:
                self.logging.critical(f"Disconnected from BYBIT {self.ws_topics} websocket feeds...reconnecting...")
                continue

            except Exception as e:
                self.logging.critical(e)
                raise e


    async def start_feed(self) -> None:
        await asyncio.gather(
            asyncio.create_task(self._open_orders_sync()),
            asyncio.create_task(self._current_position_sync()),
            asyncio.create_task(self._stream())
        )
        
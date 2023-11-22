
import asyncio
import orjson
import websockets

from frameworks.tools.logging.logger import Logger
from frameworks.exchange.hyperliquid.get.private import HyperLiquidPrivateGet
from frameworks.exchange.hyperliquid.endpoints import WsStreamLinks
from frameworks.exchange.hyperliquid.websockets.handlers.execution import HyperLiquidExecutionHandler
from frameworks.exchange.hyperliquid.websockets.handlers.order import HyperLiquidOrderHandler
# from frameworks.exchange.hyperliquid.websockets.handlers.position import hyperliquidPositionHandler
# from frameworks.exchange.hyperliquid.websockets.handlers.wallet import hyperliquidWalletHandler
# from frameworks.exchange.hyperliquid.websockets.private import hyperliquidPrivateWsInit
from frameworks.sharedstate.private import PrivateDataSharedState


class HyperLiquidPrivateStream:


    def __init__(self, sharedstate: PrivateDataSharedState, symbol: str) -> None:
        self.pdss = sharedstate
        self.symbol = symbol
        self.hlq = self.pdss.hyperliquid[symbol]

        self.logging = Logger()

        self.private_ws = HyperLiquidPrivateWsInit(
            api_secret=self.hlq["API"]["secret"]
        )

        self.private_client = HyperLiquidPrivateGet(
            sharedstate=self.pdss,
            symbol=self.symbol, 
        )

        self.ws_req, self.ws_topics = self.private_ws.multi_stream_request(
            topics=["Position", "Execution", "Order", "Wallet"]
        )

        # Create a dictionary to map topics to handlers
        self.topic_handler_map = {
            self.ws_topics[0]: HyperLiquidPositionHandler(self.pdss, self.symbol).update,
            self.ws_topics[1]: HyperLiquidExecutionHandler(self.pdss, self.symbol).update,
            self.ws_topics[2]: HyperLiquidOrderHandler(self.pdss, self.symbol).update,
            self.ws_topics[3]: HyperLiquidWalletHandler(self.pdss, self.symbol).update
        }


    async def _open_orders_sync(self) -> None:
        """
        Sync the current orders every 15s  
        """
        while True:
            recv = await self.private_client.open_orders()
            HyperLiquidOrderHandler(self.pdss, self.symbol).sync(recv)
            await asyncio.sleep(15)


    async def _current_position_sync(self) -> None:
        """
        Sync the current position & stats every 15s 
        """
        while True:
            recv = await self.private_client.current_position()
            HyperLiquidPositionHandler(self.pdss, self.symbol).sync(recv)
            await asyncio.sleep(15)


    async def _wallet_info_sync(self) -> None:
        """
        Sync the wallet information every 15s 
        """
        while True:
            recv = await self.private_client.wallet_info()
            HyperLiquidWalletHandler(self.pdss, self.symbol).sync(recv)
            await asyncio.sleep(15)


    async def _stream(self) -> None:
        async for websocket in websockets.connect(WsStreamLinks.COMBINED_FUTURES_STREAM):
            self.logging.info(f"Subscribed to HYPERLIQUID {self.ws_topics} websocket feeds...")

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
                self.logging.critical(f"Disconnected from HYPERLIQUID {self.ws_topics} websocket feeds...reconnecting...")
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
        

import asyncio
import orjson
import websockets

from src.utils.misc import curr_dt
from src.exchanges.bybit.get.private import BybitPrivateGet
from src.exchanges.bybit.endpoints import WsStreamLinks
from src.exchanges.bybit.websockets.handlers.execution import BybitExecutionHandler
from src.exchanges.bybit.websockets.handlers.order import BybitOrderHandler
from src.exchanges.bybit.websockets.handlers.position import BybitPositionHandler
from src.exchanges.bybit.websockets.private import BybitPrivateWs
from src.sharedstate import SharedState


class BybitPrivateData:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate

        self.private_ws = BybitPrivateWs(self.ss.api_key, self.ss.api_secret)
        self.private_client = BybitPrivateGet(self.ss)
        

        self.ws_req, self.ws_topics = self.private_ws.multi_stream_request(
            topics=["Position", "Execution", "Order"]
        )

        # Create a dictionary to map topics to handlers
        self.topic_handler_map = {
            self.ws_topics[0]: BybitPositionHandler(self.ss).process,
            self.ws_topics[1]: BybitExecutionHandler(self.ss).process,
            self.ws_topics[2]: BybitOrderHandler(self.ss).process,
        }


    async def open_orders_sync(self) -> None:

        while True:
            recv = await self.private_client.open_orders()
            BybitOrderHandler(self.ss).sync(recv)

            await asyncio.sleep(0.5)


    async def current_position_sync(self) -> None:

        while True:
            recv = await self.private_client.current_position()
            BybitPositionHandler(self.ss).sync(recv)

            await asyncio.sleep(0.5)


    async def private_feed(self) -> None:
        print(f"{curr_dt()}: Subscribing to BYBIT {self.ws_topics} feeds...")

        async for websocket in websockets.connect(WsStreamLinks.COMBINED_PRIVATE_STREAM):

            try:
                await websocket.send(self.private_ws.auth())
                await websocket.send(self.ws_req)

                while True:
                    recv = orjson.loads(await websocket.recv())

                    if "success" in recv:
                        continue

                    data = recv["data"]
                    handler_cls = self.topic_handler_map.get(recv["topic"])

                    if handler_cls:
                        handler_cls(data)

            except websockets.ConnectionClosed:
                continue

            except Exception as e:
                print(e)
                raise


    async def start_feed(self) -> None:
        await asyncio.gather(
            asyncio.create_task(self.open_orders_sync()),
            asyncio.create_task(self.current_position_sync()),
            asyncio.create_task(self.private_feed())
        )
        
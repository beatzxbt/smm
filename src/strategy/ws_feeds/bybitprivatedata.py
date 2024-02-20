import asyncio
import orjson
import websockets
from typing import Coroutine

from src.utils.misc import datetime_now as dt_now
from src.exchanges.bybit.get.private import BybitPrivateGet
from src.exchanges.bybit.endpoints import WsStreamLinks
from src.exchanges.bybit.websockets.handlers.order import BybitOrderHandler
from src.exchanges.bybit.websockets.handlers.position import BybitPositionHandler
from src.exchanges.bybit.websockets.private import BybitPrivateWs
from src.sharedstate import SharedState

class BybitPrivateData:
    """
    Manages private data streams from Bybit, including position, execution, and order updates.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState for managing and sharing application data.
    private_ws : BybitPrivateWs
        A BybitPrivateWs instance for WebSocket connections with authentication.
    private_client : BybitPrivateGet
        A client for fetching private data via REST API.
    ws_req : str
        The WebSocket request payload for subscribing to the private data streams.
    ws_topics : list
        A list of topics for which the WebSocket connection is established.
    order_handler : BybitOrderHandler
        Handles order-related updates and synchronization.
    position_handler : BybitPositionHandler
        Handles position-related updates and synchronization.
    topic_handler_map : dict
        A mapping of topics to their corresponding handler functions.

    Methods
    -------
    _sync_() -> Coroutine:
        Periodically synchronizes the latest open orders and current positions.
    _stream_() -> Coroutine:
        Establishes a WebSocket connection and listens for incoming private messages.
    start_feed() -> Coroutine:
        Starts the WebSocket stream and synchronization tasks to receive live private market data.
    """

    _topics_ = ["Position", "Order"]

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BybitPrivateData with a SharedState instance and sets up WebSocket connections.

        Parameters
        ----------
        ss : SharedState
            The shared state instance for managing application data.
        """
        self.ss = ss
        self.private_ws = BybitPrivateWs(self.ss.api_key, self.ss.api_secret)
        self.private_client = BybitPrivateGet(self.ss)
        
        self.ws_req, self.ws_topics = self.private_ws.multi_stream_request(
            topics=self._topics_
        )

        self.order_handler = BybitOrderHandler(self.ss)
        self.position_handler = BybitPositionHandler(self.ss)

        self.topic_handler_map = {
            self.ws_topics[0]: self.position_handler.process,
            self.ws_topics[1]: self.order_handler.process,
        }

    async def _sync_(self) -> Coroutine:
        """
        Synchronizes open orders and current positions at regular intervals.
        """
        while True:
            open_orders = await self.private_client.open_orders()
            current_position = await self.private_client.current_position()
            self.order_handler.sync(open_orders)
            self.position_handler.sync(current_position)
            await asyncio.sleep(10)

    async def _stream_(self) -> Coroutine:
        """
        Connects to Bybit's combined private WebSocket stream and handles incoming updates.
        """
        print(f"{dt_now()}: Connected to {self.ws_topics} bybit feeds...")

        async for websocket in websockets.connect(WsStreamLinks.COMBINED_PRIVATE_STREAM):
            try:
                await websocket.send(self.private_ws.authentication())
                await websocket.send(self.ws_req)

                while True:
                    recv = orjson.loads(await websocket.recv())

                    if "success" in recv:
                        continue

                    handler = self.topic_handler_map.get(recv["topic"])

                    if handler:
                        handler(recv["data"])

            except websockets.ConnectionClosed:
                continue

            except Exception as e:
                print(f"{dt_now()}: Error with bybit private feed: {e}")
                raise e

    async def start_feed(self) -> Coroutine:
        """
        Initiates the streaming and synchronization of live private market data from Bybit.
        """
        await asyncio.gather(
            asyncio.create_task(self._sync_()),
            asyncio.create_task(self._stream_())
        )
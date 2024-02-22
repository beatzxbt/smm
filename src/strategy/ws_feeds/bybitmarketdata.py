import orjson
import websockets
from typing import Coroutine, Union

from src.utils.misc import datetime_now as dt_now
from src.exchanges.bybit.get.public import BybitPublicClient
from src.exchanges.bybit.endpoints import WsStreamLinks
from src.exchanges.bybit.websockets.handlers.kline import BybitKlineHandler
from src.exchanges.bybit.websockets.handlers.orderbook import BybitBBAHandler
from src.exchanges.bybit.websockets.handlers.ticker import BybitTickerHandler
from src.exchanges.bybit.websockets.handlers.trades import BybitTradesHandler
from src.exchanges.bybit.websockets.public import BybitPublicWs
from src.sharedstate import SharedState

class BybitMarketData:
    """
    Manages market data streams from Bybit, including order book, BBA, trades, ticker, and kline.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState for managing and sharing application data.
    public_ws : BybitPublicWs
        A BybitPublicWs instance for WebSocket connections.
    ws_req : str
        The WebSocket request payload for subscribing to the market data streams.
    ws_topics : list
        A list of topics for which the WebSocket connection is established.
    topic_handler_map : dict
        A mapping of topics to their corresponding handler functions.

    Methods
    -------
    _initialize_():
        Initializes the market data by fetching the latest klines and trades.
    _stream_():
        Establishes a WebSocket connection and listens for incoming messages.
    start_feed() -> Coroutine:
        Starts the WebSocket stream to receive live market data.
    """

    _topics_ = ["Orderbook", "BBA", "Trades", "Ticker", "Kline"]

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BybitMarketData with a SharedState instance and sets up WebSocket connections.

        Parameters
        ----------
        ss : SharedState
            The shared state instance for managing application data.
        """
        self.ss = ss
        self.public_ws = BybitPublicWs(self.ss)
        self.ws_req, self.ws_topics = self.public_ws.multi_stream_request(
            topics=self._topics_, 
            depth=500, 
            interval=1
        )

        self.topic_handler_map = {
            self.ws_topics[0]: self.ss.bybit_book.process,
            self.ws_topics[1]: BybitBBAHandler(self.ss).process,
            self.ws_topics[2]: BybitTradesHandler(self.ss).process,
            self.ws_topics[3]: BybitTickerHandler(self.ss).process,
            self.ws_topics[4]: BybitKlineHandler(self.ss).process,
        }

    async def _initialize_(self) -> None:
        """
        Fetches the latest klines and trades data to initialize the market data before streaming.
        """
        klines = await BybitPublicClient(self.ss).klines(1, 500)
        trades = await BybitPublicClient(self.ss).trades(1000)
        BybitKlineHandler(self.ss).initialize(klines["result"]["list"])
        BybitTradesHandler(self.ss).initialize(trades["result"]["list"])

    async def _get_precision_(self) -> None:
        """
        Fetches and assigns the symbol's tick & lot size to the shared market data before streaming.
        """
        info = (await BybitPublicClient(self.ss).instrument_info())["result"]["list"][0]
        self.ss.bybit_tick_size = float(info["priceFilter"]["tickSize"])
        self.ss.bybit_lot_size = float(info["lotSizeFilter"]["qtyStep"])

    async def _stream_(self) -> Union[Coroutine, None]:
        """
        Asynchronously listens for messages on the WebSocket and dispatches them to the appropriate handlers.
        """
        await self._initialize_()
        await self._get_precision_()

        async for websocket in websockets.connect(WsStreamLinks.FUTURES_PUBLIC_STREAM):
            print(f"{dt_now()}: Connected to {self.ws_topics} bybit feeds...")
            self.ss.bybit_ws_connected = True

            try:
                await websocket.send(self.ws_req)

                while True:
                    recv = orjson.loads(await websocket.recv())

                    if "success" in recv:
                        continue

                    handler = self.topic_handler_map.get(recv["topic"])

                    if handler:
                        handler(recv)

            except websockets.ConnectionClosed:
                continue

            except Exception as e:
                print(f"{dt_now()}: Error with bybit public feed: {e}")
                raise e

    async def start_feed(self) -> Coroutine:
        """
        Starts the WebSocket stream to continuously receive and handle live market data.
        """
        await self._stream_()
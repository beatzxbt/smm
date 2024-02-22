import orjson
import websockets
from typing import Coroutine, Union

from src.utils.misc import datetime_now as dt_now
from src.exchanges.binance.get.client import BinancePublicGet
from src.exchanges.binance.websockets.handlers.orderbook import BinanceBBAHandler
from src.exchanges.binance.websockets.handlers.trades import BinanceTradesHandler
from src.exchanges.binance.websockets.public import BinancePublicWs
from src.sharedstate import SharedState

class BinanceMarketData:
    """
    Handles market data streams from Binance, including order book, BBA, and trades.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState for managing and sharing application data.
    public_ws : BinancePublicWs
        A BinancePublicWs instance for WebSocket connections.
    ws_url : str
        The WebSocket URL for subscribing to the market data streams.
    ws_topics : list
        A list of topics for which the WebSocket connection is established.
    stream_handler_map : dict
        A mapping of topics to their corresponding handler functions.

    Methods
    -------
    _initialize_() -> Coroutine:
        Initializes the market data by fetching the latest order book and trades.
    _stream_():
        Establishes a WebSocket connection and listens for incoming messages.
    start_feed() -> Coroutine:
        Starts the WebSocket stream to receive live market data.
    """

    _topics_ = ["Orderbook", "BBA", "Trades"]

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BinanceMarketData with a SharedState instance and sets up WebSocket connections.

        Parameters
        ----------
        ss : SharedState
            The shared state instance for managing application data.
        """
        self.ss = ss
        self.public_ws = BinancePublicWs(self.ss)
        self.ws_url, self.ws_topics = self.public_ws.multi_stream_request(topics=self._topics_)

        self.stream_handler_map = {
            self.ws_topics[0]: self.ss.binance_book.process,
            self.ws_topics[1]: BinanceBBAHandler(self.ss).process,
            self.ws_topics[2]: BinanceTradesHandler(self.ss).process,
        }

    async def _initialize_(self) -> None:
        """
        Fetches the latest order book and trades data to initialize the market data before streaming.
        """
        book = await BinancePublicGet(self.ss).orderbook(500)
        trades = await BinancePublicGet(self.ss).trades(1000)
        self.ss.binance_book.process_snapshot(book)
        BinanceTradesHandler(self.ss).initialize(trades)

    async def _get_precision_(self) -> None:
        """
        Fetches and assigns the symbol's tick & lot size to the shared market data before streaming.
        """
        info = await BinancePublicGet(self.ss).instrument_info()
        self.ss.binance_tick_size = float(info["filters"][0]["tickSize"])
        self.ss.binance_lot_size = float(info["filters"][1]["stepSize"])

    async def _stream_(self) -> Union[Coroutine, None]:
        """
        Asynchronously listens for messages on the WebSocket and dispatches them to the appropriate handlers.
        """
        await self._initialize_()
        await self._get_precision_()

        async for websocket in websockets.connect(self.ws_url):
            print(f"{dt_now()}: Connected to {self.ws_topics} binance feeds...")
            self.ss.binance_ws_connected = True

            try:
                while True:
                    recv = orjson.loads(await websocket.recv())

                    if "success" in recv:
                        continue

                    handler = self.stream_handler_map.get(recv["stream"])

                    if handler:
                        handler(recv)

            except websockets.ConnectionClosed:
                continue

            except Exception as e:
                print(f"{dt_now()}: Error with binance public feed: {e}")
                raise e

    async def start_feed(self) -> Coroutine:
        """
        Starts the WebSocket stream to continuously receive and handle live market data.
        """
        await self._stream_()
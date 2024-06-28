import asyncio
import aiohttp
import orjson
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Callable, Optional

from frameworks.tools.logging import Logger


class WebsocketStream(ABC):
    _success_ = set((aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY))
    _failure_ = set((aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR))
    _conns_ = 1  # NOTE: Handlers don't support duplicate detection yet!

    def __init__(self) -> None:
        """
        Initializes the WebsocketStream class with public and private aiohttp sessions.

        Attributes
        ----------
        public : aiohttp.ClientSession
            The aiohttp session for public WebSocket connections.

        private : aiohttp.ClientSession
            The aiohttp session for private WebSocket connections.
        """
        self.public = aiohttp.ClientSession()
        self.private = aiohttp.ClientSession()

    def load_required_refs(self, logging: Logger, symbol: str, data: Dict) -> None:
        """
        Loads required references such as logging, symbol, and data.

        Parameters
        ----------
        logging : Logger
            The Logger instance for logging events and messages.

        symbol : str
            The trading symbol.

        data : dict
            A dictionary holding various shared state data.
        """
        self.logging = logging
        self.symbol = symbol
        self.data = data

    @abstractmethod
    def create_handlers(self) -> None:
        """
        Abstract method to create handlers for the WebSocket streams.

        This method should be called in .start() *after* self.load_required_refs is completed.
        """
        pass

    @abstractmethod
    async def refresh_orderbook_data(self, timer: int = 600) -> None:
        """
        Periodically fetches and updates the order book data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass

    @abstractmethod
    async def refresh_trades_data(self, timer: int = 600) -> None:
        """
        Periodically fetches and updates trade data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass

    @abstractmethod
    async def refresh_ohlcv_data(self, timer: int = 600) -> None:
        """
        Periodically fetches and updates OHLCV data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass

    @abstractmethod
    async def refresh_ticker_data(self, timer: int = 600) -> None:
        """
        Periodically fetches and updates ticker data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass

    @abstractmethod
    def public_stream_sub(self) -> Tuple[str, List[Dict]]:
        """
        Prepares the subscription request for public WebSocket channels.

        Returns
        -------
        Tuple[str, List[Dict]]
            A tuple containing the WebSocket URL and the formatted subscription request list.
        """
        pass

    @abstractmethod
    async def public_stream_handler(self, recv: Dict) -> None:
        """
        Handles incoming messages from the public WebSocket stream.

        Parameters
        ----------
        recv : Dict
            The received message dictionary.

        Raises
        ------
        KeyError
            If the received message does not contain expected keys or handler mappings.
        """
        pass

    @abstractmethod
    async def private_stream_sub(self) -> Tuple[str, List[Dict]]:
        """
        Prepares the authentication and subscription messages for the private WebSocket channels.

        Returns
        -------
        Tuple[str, List[Dict]]
            A tuple containing the WebSocket URL and the formatted subscription request list.
        """
        pass

    @abstractmethod
    async def private_stream_handler(self, recv: Dict) -> None:
        """
        Handles incoming messages from the private WebSocket stream.

        Parameters
        ----------
        recv : Dict
            The received message dictionary.

        Raises
        ------
        KeyError
            If the received message does not contain expected keys or handler mappings.
        """
        pass

    async def send(
        self, ws: aiohttp.ClientWebSocketResponse, stream_str: str, payload: Dict
    ) -> None:
        """
        Sends a payload through the WebSocket stream.

        Parameters
        ----------
        ws : aiohttp.ClientWebSocketResponse
            The WebSocket connection instance.

        stream_str : str
            The stream type (public or private).

        payload : Dict
            The payload to be sent.


        Raises
        ------
        Exception
            If there is an issue sending the payload.
        """
        try:
            await self.logging.debug(f"Sending {stream_str} ws payload: {payload}")
            await ws.send_json(payload)
        except Exception as e:
            await self.logging.error(
                f"Failed to send {stream_str.lower()} ws payload: {payload} | Error: {e}"
            )

    async def _single_conn_(
        self,
        url: str,
        handler_map: Callable,
        on_connect: List[Dict],
        private: bool,
    ) -> bool:
        """
        Manages a single WebSocket connection.

        Parameters
        ----------
        url : str
            The WebSocket URL.

        handler_map : Callable
            The function to handle incoming messages.

        on_connect : list of dict
            The messages to send upon connection.

        private : bool
            Flag to indicate if the connection is private.


        Returns
        -------
        bool
            Flag indicating if a reconnection is needed.

        Raises
        ------
        Exception
            If there is an issue with the WebSocket connection.
        """
        session = self.private if private else self.public
        stream_str = "private" if private else "public"

        try:
            await self.logging.info(f"Attempting to start {stream_str} ws stream...")

            async with session.ws_connect(url) as ws:
                for payload in on_connect:
                    await self.send(ws, stream_str, payload)

                async for msg in ws:
                    if msg.type in self._success_:
                        await handler_map(orjson.loads(msg.data))

                    elif msg.type in self._failure_:
                        await self.logging.warning(
                            f"{stream_str} ws closed/error, reconnecting..."
                        )

                    else:
                        raise Exception(f"Unknown ws aioHTTP message type: {msg.type}")

        except asyncio.CancelledError:
            return False

        except Exception as e:
            await self.logging.error(f"{stream_str} ws: {e}")
            await self.logging.debug(f"Faulty {stream_str.lower()} payload: {e}")
            return True

    async def _create_reconnect_task_(
        self, url: str, handler_map: Callable, on_connect: List[Dict], private: bool
    ) -> None:
        """
        Creates a task to manage reconnections.

        Parameters
        ----------
        url : str
            The WebSocket URL.

        handler_map : Callable
            The function to handle incoming messages.

        on_connect : list of dict
            The messages to send upon connection.

        private : bool
            Flag to indicate if the connection is private.

        """
        while True:
            reconnect = await self._single_conn_(url, handler_map, on_connect, private)
            await self.logging.debug(
                f"Attempting to reconnect ws task, status: [{reconnect}]"
            )
            if not reconnect:
                break
            await asyncio.sleep(1.0)

    async def _manage_connections_(
        self, url: str, handler_map: Callable, on_connect: List[Dict], private: bool
    ) -> None:
        """
        Manages multiple WebSocket connections.

        Parameters
        ----------
        url : str
            The WebSocket URL.

        handler_map : Callable
            The function to handle incoming messages.

        on_connect : list of dict
            The messages to send upon connection.

        private : bool
            Flag to indicate if the connection is private.

        """
        tasks = [
            self._create_reconnect_task_(url, handler_map, on_connect, private)
            for _ in range(self._conns_)
        ]
        await asyncio.gather(*tasks)

    async def start_public_ws(
        self, url: str, handler_map: Callable, on_connect: Optional[List[Dict]] = None
    ) -> None:
        """
        Starts the public WebSocket connection.

        Parameters
        ----------
        url : str
            The WebSocket URL.

        handler_map : Callable
            The function to handle incoming messages.

        on_connect : list of dict, optional
            The messages to send upon connection.
        """
        on_connect = [] if on_connect is None else on_connect
        await self._manage_connections_(url, handler_map, on_connect, private=False)

    async def start_private_ws(
        self, url: str, handler_map: Callable, on_connect: Optional[List[Dict]] = None
    ) -> None:
        """
        Starts the private WebSocket connection.

        Parameters
        ----------
        url : str
            The WebSocket URL.

        handler_map : Callable
            The function to handle incoming messages.

        on_connect : list of dict, optional
            The messages to send upon connection.
        """
        on_connect = [] if on_connect is None else on_connect
        await self._manage_connections_(url, handler_map, on_connect, private=True)

    @abstractmethod
    async def start(self) -> None:
        """
        Starts all necessary asynchronous tasks for Websocket stream management and data refreshing.
        """
        pass

    async def shutdown(self) -> None:
        """
        Shuts down the WebSocket connections by closing the aiohttp sessions.
        """
        await self.public.close()
        await self.private.close()

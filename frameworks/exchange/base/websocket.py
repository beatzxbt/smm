import asyncio
import aiohttp
import orjson
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Callable, Optional, Coroutine

from frameworks.tools.logging import Logger


class WebsocketStream(ABC):
    _success_ = set((aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY))
    _failure_ = set((aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR))
    _conns_ = 1

    def __init__(self, logger: Logger) -> None:
        self.logging = logger
        self.public = aiohttp.ClientSession()
        self.private = aiohttp.ClientSession()

    @abstractmethod
    async def refresh_orderbook_data(self, timer: int=600) -> None:
        """
        Periodically fetches and updates the order book data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass

    @abstractmethod
    async def refresh_trades_data(self, timer: int=600) -> None:
        """
        Periodically fetches and updates trade data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass

    @abstractmethod
    async def refresh_ohlcv_data(self, timer: int=600) -> None:
        """
        Periodically fetches and updates OHLCV data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass
    
    @abstractmethod
    async def refresh_ticker_data(self, timer: int=600) -> None:
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
        Prepares the subscription request for public Websocket channels.

        Returns
        -------
        Tuple[str, List[Dict]]
            A tuple containing the Websocket URL and the formatted subscription request list.
        """
        pass
    
    @abstractmethod
    async def public_stream_handler(self, recv: Dict) -> None:
        """
        Handles incoming messages from the public Websocket stream.

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
        Prepares the authentication and subscription messages for the private Websocket channels.

        Returns
        -------
        Tuple[str, List[Dict]]
            A tuple containing the Websocket URL and the formatted subscription request list.
        """
        pass

    @abstractmethod
    async def private_stream_handler(self, recv: Dict) -> None:
        """
        Handles incoming messages from the private Websocket stream.

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
        """Send payload through websocket stream"""
        try:
            await ws.send_json(payload)
        except Exception as e:
            await self.logging.error(f"Failed to submit {stream_str.lower()} ws payload: {payload}")
            raise e

    async def _single_conn_(
        self,
        url: str,
        handler_map: Callable,
        on_connect: Optional[List[Dict]],
        private: bool,
    ) -> bool:
        session = self.private if private else self.public
        stream_str = "Private" if private else "Public"

        try:
            async with session.ws_connect(url) as ws: 
                for payload in on_connect:
                    await self.send(ws, stream_str, payload)

                async for msg in ws:
                    if msg.type in self._success_:
                        handler_map(orjson.loads(msg.data))

                    elif msg.type in self._failure_:
                        await self.logging.warning(f"{stream_str} ws closed/error occurred, reconnecting...")

                    else:
                        raise Exception(f"Unknown websocket aioHTTP message type: {msg.type}")

        except asyncio.CancelledError:
            return False

        except Exception as e:
            await self.logging.error(f"Issue with {stream_str.lower()} occured: {e}")
            return True

    async def _create_reconnect_task_(self, url: str, handler_map: Callable, on_connect: Optional[List[Dict]], private: bool) -> None:
        while True:
            reconnect = await self._single_conn_(url, handler_map, on_connect, private)
            if not reconnect:
                break 
            await asyncio.sleep(1)

    async def _manage_connections_(self, url: str, handler_map: Callable, on_connect: Optional[List[Dict]], private: bool) -> None:
        tasks = [self._create_reconnect_task_(url, handler_map, on_connect, private) for _ in range(self._conns_)]
        await asyncio.gather(*tasks)

    async def start_public_ws(
        self,
        url: str,
        handler_map: Callable,
        on_connect: Optional[List[Dict]]=[],
    ) -> Coroutine:
        await self._manage_connections_(url, handler_map, on_connect, private=False)

    async def start_private_ws(
        self,
        url: str,
        handler_map: Callable,
        on_connect: Optional[List[Dict]]=[],
    ) -> Coroutine:
        await self._manage_connections_(url, handler_map, on_connect, private=True)

    async def shutdown(self) -> None:
        await self.public.close()
        await self.private.close()
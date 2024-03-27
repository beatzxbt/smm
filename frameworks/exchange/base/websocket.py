import asyncio
import aiohttp
import orjson
from abc import ABC
from typing import List, Dict, Callable, Optional, Coroutine
from frameworks.tools.logging import Logger


class WebsocketStream(ABC):
    _success_ = set((aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY))
    _failure_ = set((aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR))
    _conns_ = 1

    def __init__(self) -> None:
        self.public = aiohttp.ClientSession()
        self.private = aiohttp.ClientSession()
        self.logging = None

    async def set_logger(self, logging: Logger) -> None:
        if self.logging is None:
            self.logging = logging
        else:
            raise Exception("Logger is not set in inherited class!")

    async def send(
        self, ws: aiohttp.ClientWebSocketResponse, stream_str: str, payload: Dict
    ) -> None:
        """Send payload through websocket stream"""
        try:
            await ws.send_json(payload)
        except Exception as e:
            self.logging.error(f"Failed to submit {stream_str.lower()} ws payload: {payload}")
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
                        self.logging.warning(f"{stream_str} ws closed/error occurred, reconnecting...")

                    else:
                        raise Exception(f"Unknown websocket aioHTTP message type: {msg.type}")

        except asyncio.CancelledError:
            return False

        except Exception as e:
            self.logging.error(f"Issue with {stream_str.lower()} occured: {e}")
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
        on_connect: Optional[List[Dict]] = [],
    ) -> Coroutine:
        await self._manage_connections_(url, handler_map, on_connect, private=False)

    async def start_private_ws(
        self,
        url: str,
        handler_map: Callable,
        on_connect: Optional[List[Dict]] = [],
    ) -> Coroutine:
        await self._manage_connections_(url, handler_map, on_connect, private=True)

    async def shutdown(self) -> None:
        await self.public.close()
        await self.private.close()
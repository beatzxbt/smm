import asyncio
import aiohttp
import orjson
from frameworks.tools.logger import Logger
from typing import List, Dict, Union

class WebsocketStream:

    def __init__(self, logger: Logger) -> None:
        self.logging = logger
        self.session = aiohttp.ClientSession()
        self.connected = False

    async def _connect_(self, url: str):
        """Start a websocket connection"""
        try:
            self.ws = await self.session.ws_connect(url)
            self.connected = True
        except Exception as e:
            self.logging.error(f"Error connecting to {url}: {e}")
            self.connected = False
            raise e

    async def _send_(self, payload: Union[Dict, List]):
        """Send payload through session"""
        if self.connected:
            await self.ws.send_json(payload)
        else:
            self.logging.error(f"Session not started!")

    def _handler_map_(self, recv: Union[Dict, List]):
        """Map a received msg to its respective handler"""
        raise NotImplementedError("Must be implemented in inherited class!")

    async def start(self, url: str):
        try:
            await self._connect_(url)
            while True:
                msg = await self.ws.receive()

                if msg.type in [aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY]:
                    recv = orjson.loads(msg.data)
                    self._handler_map_(recv["stream"])(recv)

                elif msg.type in [aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR]:
                    break

        except aiohttp.ClientConnectionError:
            self.logging.error("Disconnected from websocket feeds, reconnecting...")
            await asyncio.sleep(1)
            await self.start(url)

        except Exception as e:
            self.logging.critical(f"Exception in websocket stream: {e}")
            raise e

    async def close(self):
        await self.ws.close()
        await self.session.close()
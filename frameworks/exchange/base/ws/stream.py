import asyncio
import aiohttp
import orjson
from frameworks.sharedstate import SharedState
from typing import Tuple, List, Dict, Optional, Union


class WebsocketStream:

    def __init__(self) -> None:
        self.exchange = None
        self.ws_url = None
        self.ws_topics = None
        self.ws_handler_map = None

        self.session = aiohttp.ClientSession()
        self.active_session = False

    async def connect(self, url: str):
        """Start ws session"""
        await self.session.ws_connect(url)
        self.active_session = True

    async def send(self, payload: Union[Dict, List]):
        """Send payload through session"""
        pass

    async def start(self):
        if self.active_session:
            try:
                while True:
                    recv = orjson.loads(await self.session.e())

                    if "success" not in recv:
                        handler = self.stream_handler_map.get(recv["stream"])

                        if handler:
                            handler(recv)

            except aiohttp.ClientConnectionError:
                self.logging.critical(f"Disconnected from websocket feeds, reconnecting...")
                pass

            except Exception as e:
                self.logging.critical(e)
                raise e

        else:
            self.logging.critical(f"Websocket connection inactive!")

    async def start_feed(self):
        await self._stream()

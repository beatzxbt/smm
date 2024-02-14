import zmq
import asyncio
import aiohttp
import orjson
from typing import List, Dict, Callable, Optional
from frameworks.tools.logger import Logger


class WebsocketStream:
    def __init__(self, private: bool=False) -> None:
        self.public = aiohttp.ClientSession()
        self._public_connected_ = False
        self.logging = None

        if private:
            self.private = aiohttp.ClientSession()
            self._private_connected_ = False

        self._success_ = [aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY]
        self._failure_ = [aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR]

    def _set_internal_logger_(self, logger: Logger) -> None:
        self.logging = logger
        return None

    async def send(self, stream: aiohttp.ClientWebSocketResponse, payload: Dict):
        """Send payload through websocket stream"""
        try:
            await stream.send_json(payload)
        except Exception as e:
            self.logging.error(f"failed to send payload to ws...")
            raise e
 
    async def public_stream(self, url: str, handler_map: Callable, on_connect: Optional[List[Dict]]=[]) -> zmq.Frame:
        """Start the public websocket connection"""
        try:
            self.public_ws = await self.public.ws_connect(url)
            self._public_connected_ = True
            await asyncio.sleep(0.5)
            for payload in on_connect:
                await self.send(self.public_ws, payload)

            while True:
                msg = await self.public_ws.receive()

                if msg.type in self._success_:
                    handler_map(orjson.loads(msg.data))

                elif msg.type in self._failure_:
                    self.logging.error("public ws closed/error occurred, reconnecting...")
                    self.public_ws = await self.public.ws_connect(url)
                    await asyncio.sleep(0.5)
                    for payload in on_connect:
                        await self.send(self.public_ws, payload)

        except Exception as e:
            self._public_connected_ = False
            raise e
        
    async def private_stream(self, url: str, handler_map: Callable, on_connect: Optional[List[Dict]]=[]) -> zmq.Frame:
        """Start the private websocket connection"""
        try:
            self.private_ws = await self.private.ws_connect(url)
            self._private_connected_ = True
            for payload in on_connect:
                await self.send(self.private_ws, payload)

            while True:
                msg = await self.private_ws.receive()

                if msg.type in self._success_:
                    handler_map(orjson.loads(msg.data))

                elif msg.type in self._failure_:
                    self.logging.error("private ws closed/error occurred, reconnecting...")
                    self.private_ws = await self.private.ws_connect(url)
                    for payload in on_connect:
                        await self.send(self.private_ws, payload)

        except Exception as e:
            self._private_connected_ = False
            raise e
    
    async def close_public(self):
        await self.public_ws.close()
        await self.public.close()

    async def close_private(self):
        await self.private_ws.close()
        await self.private.close()

    async def close_all(self):
        await self.close_public()
        await self.close_private()


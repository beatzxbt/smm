import asyncio
import hmac
import hashlib
import aiohttp
from typing import List, Optional, Union, Literal, Dict, Any, Tuple

from framework.tools.time import time_s, time_ms, time_ns
from framework.tools.logger import Logger

from framework.base.client import BaseRestTradeClient, BaseWsTradeClient

RECV_WINDOW = 5000
ENDPOINT_WS_TRADE = "wss://stream.bybit.com/v5/trade"

class BybitRestTradeClient(BaseRestTradeClient):
    def __init__(self, api_key: str, api_secret: str, logger: Logger):
        super().__init__(
            api_key=api_key, 
            api_secret=api_secret, 
            logger=logger
        )

    def sign(self, payload_str):
        timestamp = str(int(time_ms()))
        param_str = timestamp + self.api_key + str(RECV_WINDOW) + payload_str

        hash_signature = hmac.new(
            key=bytes(self.api_secret, "utf-8"),
            msg=bytes(param_str, "utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        headers = {
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-RECV-WINDOW": str(RECV_WINDOW),
            "X-BAPI-SIGN": hash_signature,
            "Content-Type": "application/json",
        }

        return headers

    async def submit(self, endpoint, payload, method):
        if not self.ensure_running():
            return {}

        payload_str = str(self.json_encoder.encode(payload))
        signed_header = self.sign(payload_str)

        try:
            time_sent = time_ms()

            if method == "GET":
                # For GET requests, convert payload to query string.
                # If the payload is empty, use the endpoint as is.
                query_string = "&".join([f"{k}={v}" for k, v in payload.items() if v is not None])
                url = f"{endpoint}?{query_string}" if query_string else endpoint
                signed_header = self.sign(query_string)
                
                async with self.session.get(
                    url=url, 
                    headers=signed_header
                ) as response:
                    time_recv = time_ms()
                    resp_text = await response.text()
                    
                    try:
                        resp_json = self.json_decoder.decode(resp_text)
                        
                        if resp_json["retCode"] == 0:
                            latency = round(time_recv - time_sent, 2)
                            self.logger.trace(f"Trade REST [{endpoint}] latency; {latency}ms")
                            return resp_json
                        else:
                            self.logger.debug(f"Trade REST [{endpoint}] request failed; {resp_json}")
                            return None
                        
                    except Exception as e:
                        self.logger.error(f"Trade REST [{endpoint}] request exception; {str(e)}")
                        return None
                    
            elif method == "POST":
                async with self.session.post(
                    url=endpoint, 
                    headers=signed_header, 
                    data=payload_str
                ) as response:
                    time_recv = time_ms()
                    resp_text = await response.text()
                    
                    try:
                        resp_json = self.json_decoder.decode(resp_text)
                        
                        if resp_json["retCode"] == 0:
                            latency = round(time_recv - time_sent, 2)
                            self.logger.trace(f"Trade REST [{endpoint}] latency; {latency}ms")
                            return resp_json
                        
                        elif resp_json["retCode"] in (
                            10002,  # Timestamp outside recvWindow
                        ):
                            self.logger.debug(f"Trade REST [{endpoint}] request error; {resp_json["retMsg"]}")
                            return resp_json
                        else:
                            self.logger.warning(f"Trade REST [{endpoint}] request failed; {resp_json}")
                            return resp_json
                    except Exception as e:
                        self.logger.error(f"Trade REST [{endpoint}] request exception; {str(e)}")
                        return None

        except Exception as e:
            self.logger.error(f"Trade REST [{endpoint}] request exception; {str(e)}")
            return None

class BybitWsTradeClient(BaseWsTradeClient):
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        logger: Logger,
    ):
        """Initialize Bybit WebSocket client.

        Args:
            api_key (str): Bybit API key.
            api_secret (str): Bybit API secret.
            logger (Logger): Logger instance.
        """
        super().__init__(
            api_key, api_secret, logger)

        self.ws = None
        self.is_active = False
        self.last_used = 0
        self.backoff_delay = 0.25
        
        self.pending_requests = {}
        self.listener_task = None
        
        self.heartbeat_interval = 10.0
        self.heartbeat_task = None
        self.reconnect_base_delay = 0.25
        self.reconnect_max_delay = 2.0

    async def authenticate(self, ws):
        if ws is None:
            raise ConnectionError("Trade WS connection not initialized")

        expire = str(int(time_ms() + 60000))
        signature = hmac.new(
            key=bytes(self.api_secret, 'utf-8'),
            msg=bytes(f"GET/realtime{expire}", 'utf-8'),
            digestmod=hashlib.sha256,
        ).hexdigest()

        auth_msg = {
            "op": "auth",
            "args": [self.api_key, expire, signature]
        }

        await ws.send_bytes(self.json_encoder.encode(auth_msg))
        auth_response = await ws.receive()
        if auth_response.type == aiohttp.WSMsgType.TEXT:
            resp = self.json_decoder.decode(auth_response.data)
            if resp.get("retCode", 0) == 0 and resp.get("op") == "auth":
                self.logger.debug("Trade WS authentication successful")
                return True
            else:
                self.logger.error(f"Trade WS authentication failed: {resp}")
                return False
        else:
            self.logger.error("Trade WS authentication failed: No valid TEXT response")
            return False

    async def _create_connection(self) -> Optional[aiohttp.ClientWebSocketResponse]:
        """Create and authenticate a new WebSocket connection.

        Returns:
            Optional[aiohttp.ClientWebSocketResponse]: The authenticated WebSocket or None if failed.
        """
        try:
            ws = await self.session.ws_connect(ENDPOINT_WS_TRADE)
            authenticated = await self.authenticate(ws)
            if authenticated:
                self.logger.debug("Connection created and authenticated.")
                return ws
            else:
                await ws.close()
                return None
        except Exception as e:
            self.logger.error(f"Failed to create connection; error: {e}")
            return None

    async def connect(self):
        try:
            self.ws = await self._create_connection()
            if self.ws:
                self.is_active = True
                self.last_used = time_ms()
                self.listener_task = asyncio.create_task(self._ws_listener())
                self.logger.info("Trade WS connection established.")
                self.is_running = True
            else:
                self.logger.error("Failed to authenticate or create Trade WS connection.")
                raise ConnectionError("Could not establish Trade WS connection.")
        except Exception as e:
            self.logger.error(f"Failed to establish Trade WS connection: {e}")
            raise ConnectionError(f"Could not establish Trade WS connection: {e}")

        # Start the heartbeat task
        if self.heartbeat_task is None:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.logger.debug("Trade WS Heartbeat task started.")

    async def _ws_listener(self):
        """Listen for messages on the WebSocket connection."""
        while True:
            try:
                if not self.is_active or self.ws is None:
                    return

                if self.ws.closed:
                    self.logger.warning("Trade WS connection closed, reconnecting...")
                    await self._reconnect()
                    continue

                async for msg in self.ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = self.json_decoder.decode(msg.data)
                        req_id = data.get("reqId")

                        # Detect a Bybit pong response
                        if data.get("op") == "pong":
                            # self.logger.debug(f"Received pong: {data}")
                            continue

                        # Correlated response
                        if req_id is not None and req_id in self.pending_requests:
                            fut = self.pending_requests.pop(req_id)
                            fut.set_result(data)
                        else:
                            self.logger.debug(f"Trade WS Uncorrelated message: {data}")

                    elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                        self.logger.warning("Trade WS connection closing or error encountered.")
                        await self._reconnect()
                        break

            except (
                aiohttp.ClientError,
                aiohttp.WSServerHandshakeError,
                aiohttp.ClientConnectorError,
            ) as e:
                self.logger.error(f"Trade WS error: {e}")
                await self._reconnect()
            except asyncio.CancelledError:
                self.logger.debug("Trade WS listener task cancelled.")
                if self.ws:
                    try:
                        await self.ws.close()
                    except Exception as exc:
                        self.logger.error(f"Trade WS error closing connection: {exc}")
                return
            except Exception as e:
                self.logger.error(f"Trade WS unexpected error: {e}")
                await self._reconnect()

    async def _heartbeat_loop(self):
        """Periodically send heartbeat (ping) messages to keep connection alive."""
        while self.is_running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self.heartbeat()
            except asyncio.CancelledError:
                self.logger.debug("Trade WS heartbeat task cancelled.")
                return
            except Exception as e:
                self.logger.error(f"Trade WS heartbeat loop error: {e}")

    async def heartbeat(self):
        """Send ping message to the connection."""
        if self.is_active and self.ws and not self.ws.closed:
            ping_msg = {
                "op": "ping",
                "req_id": str(time_ns())  # unique for correlation
            }
            try:
                await self.ws.send_bytes(self.json_encoder.encode(ping_msg))
                self.logger.debug(f"Trade WS sent ping; {ping_msg}")
            except Exception as e:
                self.logger.error(f"Trade WS failed to send ping; error: {e}")
                await self._reconnect()

    async def _reconnect(self):
        """Reconnect the WebSocket connection with an exponential backoff."""
        self.is_active = False
        ws_to_close = self.ws
        self.ws = None
        if ws_to_close:
            try:
                await ws_to_close.close()
            except Exception as e:
                self.logger.error(f"Trade WS error closing connection: {e}")

        retries = 0
        max_retries = 3

        while retries < max_retries:
            self.logger.debug(f"Trade WS reconnect attempt #{retries+1} in {self.backoff_delay}s...")
            await asyncio.sleep(self.backoff_delay)
            try:
                new_ws = await self._create_connection()
                if new_ws:
                    self.ws = new_ws
                    self.is_active = True
                    self.last_used = time_ms()
                    self.backoff_delay = self.reconnect_base_delay
                    self.logger.info("Trade WS reconnected successfully.")
                    return
                else:
                    self.logger.debug("Trade WS authentication failed on reconnect.")
            except Exception as e:
                self.logger.error(f"Trade WS reconnect failed: {e}")

            retries += 1
            # Exponential backoff up to a limit
            self.backoff_delay = min(self.backoff_delay * 2, self.reconnect_max_delay)

        self.logger.error(f"Trade WS failed to reconnect after {max_retries} attempts.")

    async def submit(self, payload: dict) -> dict:
        """Send a request payload over the WebSocket connection and wait for the correlated response.

        Args:
            payload (dict): The request payload (e.g. order create, amend, or cancel).

        Returns:
            dict: The response from the server.
        """
        if not self.is_running:
            self.logger.error("Trade WS client not initialized")
            return {}

        if not self.is_active or self.ws is None:
            self.logger.error(f"No active Trade WS connection is available; {payload}")
            return {}

        req_id = str(time_ns())
        payload["reqId"] = req_id
        future = self.ev_loop.create_future()
        self.pending_requests[req_id] = future
        time_sent = time_ms()

        try:
            await self.ws.send_bytes(self.json_encoder.encode(payload))
            response = await future
            latency = round(time_ms() - time_sent, 2)
            self.logger.trace(f"Trade WS [{payload.get('op')}] latency: {latency}ms")

            if response.get("retCode", 0) == 0:
                return response
            else:
                self.logger.debug(f"Trade WS request failed; response: {response}; payload: {payload}")
                return response

        except Exception as e:
            self.pending_requests.pop(req_id, None)
            self.logger.error(f"Trade WS error sending request: {e}")
            raise

    async def close(self):
        """Shut down the WebSocket connection gracefully."""
        self.is_running = False

        # Cancel the heartbeat task
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()

        # Cancel the listener task
        if self.listener_task and not self.listener_task.done():
            self.listener_task.cancel()

        # Close the WebSocket connection
        if self.ws and not self.ws.closed:
            try:
                await self.ws.close()
            except Exception as e:
                self.logger.error(f"Trade WS error closing connection: {e}")

        # Close the session
        if self.session:
            await self.session.close()
            self.session = None

        self.logger.info("Trade WS connection closed.")

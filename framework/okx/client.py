import asyncio
import hmac
import hashlib
import base64
import aiohttp
import msgspec
from typing import List, Optional, Union, Literal, Dict, Any, Tuple

from framework.tools import (
    time_ms, 
    time_s, 
    time_ns, 
    Logger
)

from framework.base.client import BaseRestTradeClient, BaseWsTradeClient

# OKX API endpoints
ENDPOINT_WS_PUBLIC = "wss://ws.okx.com:8443/ws/v5/public"
ENDPOINT_WS_PRIVATE = "wss://ws.okx.com:8443/ws/v5/private"
ENDPOINT_WS_BUSINESS = "wss://ws.okx.com:8443/ws/v5/business"
ENDPOINT_REST_BASE = "https://www.okx.com"
ENDPOINT_GET_OPEN_ORDERS = "/api/v5/trade/orders-pending"
ENDPOINT_GET_POSITIONS = "/api/v5/account/positions"
ENDPOINT_GET_INSTRUMENTS = "/api/v5/public/instruments"
ENDPOINT_GET_TICKERS = "/api/v5/market/tickers"
ENDPOINT_GET_TRADES = "/api/v5/market/trades"
ENDPOINT_POST_CREATE_ORDER = "/api/v5/trade/order"
ENDPOINT_POST_CREATE_BATCH = "/api/v5/trade/batch-orders"
ENDPOINT_POST_AMEND_ORDER = "/api/v5/trade/amend-order"
ENDPOINT_POST_AMEND_BATCH = "/api/v5/trade/amend-batch-orders"
ENDPOINT_POST_CANCEL_ORDER = "/api/v5/trade/cancel-order"
ENDPOINT_POST_CANCEL_BATCH = "/api/v5/trade/cancel-batch-orders"
ENDPOINT_POST_CANCEL_ALL = "/api/v5/trade/cancel-all"
ENDPOINT_POST_SET_LEVERAGE = "/api/v5/account/set-leverage"

class OkxWsTradeClient(BaseWsTradeClient):
    """OKX WebSocket Trade Client with automatic reconnect and heartbeat."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str,
        logger: Logger,
    ):
        """Initialize OKX WebSocket client.

        Args:
            api_key (str): OKX API key.
            api_secret (str): OKX API secret.
            passphrase (str): OKX API passphrase.
            logger (Logger): Logger instance.
        """
        super().__init__(api_key, api_secret, logger)

        self.passphrase = passphrase
        self.ws = None
        self.is_active = False
        self.last_used = 0
        self.backoff_delay = 0.25
        
        self.pending_requests = {}
        self.listener_task = None
        
        self.heartbeat_interval = 20.0  # OKX requires heartbeat every 30s, we do 20s to be safe
        self.heartbeat_task = None
        self.reconnect_base_delay = 0.25
        self.reconnect_max_delay = 2.0
        
        self.json_encoder = msgspec.json.Encoder()
        self.json_decoder = msgspec.json.Decoder()

    async def authenticate(self, ws: aiohttp.ClientWebSocketResponse) -> bool:
        """Authenticate the WebSocket connection with OKX.

        Args:
            ws (aiohttp.ClientWebSocketResponse): The WebSocket connection to authenticate.

        Returns:
            bool: True if authenticated, False otherwise.
        """
        if ws is None:
            raise ConnectionError("Trade WS connection not initialized")

        timestamp = str(int(time_s()))
        message = timestamp + 'GET' + '/users/self/verify'
        
        # Create signature
        signature = base64.b64encode(
            hmac.new(
                key=self.api_secret.encode('utf-8'),
                msg=message.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
        ).decode('utf-8')
        
        # Create auth message
        auth_msg = {
            "op": "login",
            "args": [{
                "apiKey": self.api_key,
                "passphrase": self.passphrase,
                "timestamp": timestamp,
                "sign": signature
            }]
        }

        await ws.send_str(self.json_encoder.encode(auth_msg).decode())
        auth_response = await ws.receive()
        if auth_response.type == aiohttp.WSMsgType.TEXT:
            resp = self.json_decoder.decode(auth_response.data)
            if resp.get("code") == "0" and resp.get("op") == "login":
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
            ws = await self.session.ws_connect(ENDPOINT_WS_BUSINESS)
            authenticated = await self.authenticate(ws)
            if authenticated:
                self.logger.debug("Connection created and authenticated.")
                return ws
            else:
                await ws.close()
        except Exception as e:
            self.logger.error(f"Failed to create connection: {e}")

        return None

    async def connect(self):
        """Establish WebSocket connection and start the heartbeat."""
        if not self.session:
            self.session = aiohttp.ClientSession()

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
                        
                        # Detect a pong response
                        if data.get("op") == "pong":
                            self.logger.trace("Received pong")
                            continue

                        # Handle request responses
                        if "id" in data:
                            req_id = data.get("id")
                            if req_id in self.pending_requests:
                                fut = self.pending_requests.pop(req_id)
                                fut.set_result(data)
                            else:
                                self.logger.debug(f"Trade WS Uncorrelated message: {data}")
                        else:
                            self.logger.debug(f"Trade WS message: {data}")

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
                await self._send_heartbeat()
            except asyncio.CancelledError:
                self.logger.debug("Trade WS heartbeat task cancelled.")
                return
            except Exception as e:
                self.logger.error(f"Trade WS heartbeat loop error: {e}")

    async def _send_heartbeat(self):
        """Send ping message to the connection."""
        if self.is_active and self.ws and not self.ws.closed:
            ping_msg = {
                "op": "ping"
            }
            try:
                await self.ws.send_str(self.json_encoder.encode(ping_msg).decode())
                self.logger.trace("Trade WS sent ping")
            except Exception as e:
                self.logger.error(f"Trade WS failed to send ping, reconnecting... Error: {e}")
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

    async def submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request payload over the WebSocket connection and wait for the correlated response.

        Args:
            payload (Dict[str, Any]): The request payload (e.g. order create, amend, or cancel).

        Returns:
            Dict[str, Any]: The response from the server.
        """
        if not self.is_running:
            self.logger.error("Trade WS client not initialized")
            return {}

        if not self.is_active or self.ws is None:
            self.logger.error(f"No active Trade WS connection is available; {payload}")
            return {}

        req_id = str(time_ns())
        payload["id"] = req_id
        future = self.ev_loop.create_future()
        self.pending_requests[req_id] = future
        time_sent = time_ms()

        try:
            await self.ws.send_str(self.json_encoder.encode(payload).decode())
            response = await future
            latency = round(time_ms() - time_sent, 2)
            self.logger.trace(f"Trade WS request latency: {latency}ms")
            
            # Check success patterns
            if response.get("code") == "0":
                return response
            else:
                self.logger.debug(f"Trade WS request completed with response: {response}")
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

class OkxRestTradeClient(BaseRestTradeClient):
    def __init__(self, api_key: str, api_secret: str, passphrase: str, logger: Logger):
        super().__init__(api_key, api_secret, logger)
        self.passphrase = passphrase

    def sign(self, timestamp, method, request_path, body=''):
        if body and isinstance(body, dict):
            body = self.json_encoder.encode(body).decode()
        
        message = timestamp + method + request_path + (body or '')
        
        mac = hmac.new(
            bytes(self.api_secret, encoding='utf-8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        d = mac.digest()
        
        return base64.b64encode(d).decode()

    async def submit(self, endpoint, payload, method):
        if not self.ensure_running():
            return {}

        timestamp = str(int(time_ms() / 1000))
        
        # For GET requests, convert payload to query string
        if method == "GET" and payload:
            query_string = "&".join([f"{k}={v}" for k, v in payload.items() if v is not None])
            request_path = f"{endpoint}?{query_string}"
            body = ''
        else:
            request_path = endpoint
            body = payload if method == "POST" else ''
        
        # Generate signature
        signature = self.sign(timestamp, method, request_path, body)
        
        # Set headers
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json"
        }

        try:
            time_sent = time_ms()
            url = f"{ENDPOINT_REST_BASE}{request_path}"

            if method == "GET":
                async with self.session.get(
                    url=url, 
                    headers=headers
                ) as response:
                    time_recv = time_ms()
                    resp_text = await response.text()
                    
                    try:
                        resp_json = self.json_decoder.decode(resp_text)
                        
                        if resp_json.get("code") == "0":
                            latency = round(time_recv - time_sent, 2)
                            self.logger.trace(f"Trade REST [{endpoint}] latency; {latency}ms")
                            return resp_json
                        else:
                            self.logger.warning(f"Trade REST [{endpoint}] request failed; {resp_json}")
                            return resp_json
                        
                    except Exception as e:
                        self.logger.error(f"Trade REST [{endpoint}] request exception; {str(e)}")
                        return None
                    
            elif method == "POST":
                payload_json_str = self.json_encoder.encode(payload).decode() if payload else ''
                
                async with self.session.post(
                    url=url, 
                    headers=headers, 
                    data=payload_json_str
                ) as response:
                    time_recv = time_ms()
                    resp_text = await response.text()
                    
                    try:
                        resp_json = self.json_decoder.decode(resp_text)
                        
                        if resp_json.get("code") == "0":
                            latency = round(time_recv - time_sent, 2)
                            self.logger.trace(f"Trade REST [{endpoint}] latency; {latency}ms")
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
import asyncio
import hashlib
import hmac
from typing import Any, Optional

import aiohttp
import msgspec

from framework.base.common import Venue
from framework.base.trading.client import HttpClient, HttpMethod, WsClient
from framework.base.trading.models import (
    ClientResponse,
    ClientResponseTransport,
    Secret,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.time import time_ms, time_ns


def _resolve_secrets(
    load_secrets: bool, key: str | None, secret: str | None
) -> tuple[str, str]:
    if load_secrets:
        return (
            Secret.load("BINANCE_API_KEY").value,
            Secret.load("BINANCE_API_SECRET").value,
        )
    return (key or ""), (secret or "")


class BinanceHttpClient(HttpClient):
    """HTTP API client for Binance Futures."""

    BASE_URLS = {
        Venue.BINANCE_USDM: "https://fapi.binance.com/fapi",
        Venue.BINANCE_COINM: "https://dapi.binance.com/dapi",
    }

    def __init__(
        self,
        logger: Logger,
        load_secrets: bool,
        is_usd_margined: bool = True,
    ):
        """Initialize the Binance HTTP client."""
        super().__init__(
            venue=Venue.BINANCE_USDM if is_usd_margined else Venue.BINANCE_COINM,
            logger=logger,
            load_secrets=load_secrets,
        )
        if self.load_secrets:
            self.key = Secret.load("BINANCE_API_KEY").value
            self.secret = Secret.load("BINANCE_API_SECRET").value
        else:
            self.key = ""
            self.secret = ""
        self.base_url = self.BASE_URLS[self.venue]

    def sign(self, method: HttpMethod, endpoint: str, body: dict) -> dict:
        """Generate authentication signature for Binance API requests."""
        params = body.copy()
        params["timestamp"] = time_ms()
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(
            key=self.secret.encode("utf-8"),
            msg=query_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        params["signature"] = signature.hexdigest()
        return params

    async def request[T](
        self,
        method: HttpMethod,
        endpoint: str,
        params: dict,
        data: dict,
        sign: bool,
        decoder: msgspec.json.Decoder[T],
    ) -> ClientResponse[T]:
        """Make an HTTP request to the Binance API.

        Args:
            method (HttpMethod): HTTP method.
            endpoint (str): API endpoint.
            params (dict): Query parameters.
            data (dict): Request body.
            sign (bool): Whether to sign the request.

        Returns:
            ClientResponse[T]: The response object.

        """
        started_ns = time_ns()
        url = self.base_url + endpoint
        headers = {"X-MBX-APIKEY": self.key}
        req_params = params.copy() if params else {}
        req_data = data.copy() if data else {}

        if sign:
            # Binance expects all params (query and body) to be signed
            all_params = {**req_params, **req_data}
            signed_params = self.sign(method, endpoint, all_params)
            req_params = signed_params
            req_data = {}

        try:
            async with self.session.request(
                method=method.value,
                url=url,
                params=req_params,
                json=req_data if req_data else None,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                result = decoder.decode(await resp.read())
                return self.make_success(
                    data=result,
                    meta=self.make_meta(
                        transport=ClientResponseTransport.HTTP,
                        operation=endpoint,
                        started_ns=started_ns,
                        finished_ns=time_ns(),
                        status_code=resp.status,
                        attempt=1,
                    ),
                )
        except Exception as e:
            self.logger.warning(f"{self.__class__.__name__} request error: {e}")
            return self.make_failure(
                meta=self.make_meta(
                    transport=ClientResponseTransport.HTTP,
                    operation=endpoint,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    status_code=(
                        e.status if isinstance(e, aiohttp.ClientResponseError) else None
                    ),
                    attempt=1,
                    timeout=isinstance(e, asyncio.TimeoutError),
                ),
                err_no=1,
                err_msg=str(e),
            )


class BinanceWsClient(WsClient):
    """WebSocket API client for Binance Futures."""

    BASE_URLS = {
        Venue.BINANCE_USDM: "wss://fstream.binance.com/ws",
        Venue.BINANCE_COINM: "wss://dstream.binance.com/ws",
    }

    def __init__(
        self,
        logger: Logger,
        load_secrets: bool = False,
        is_usd_margined: bool = True,
        key: str | None = None,
        secret: str | None = None,
    ):
        """Initialize the Binance WebSocket client."""
        super().__init__(
            venue=Venue.BINANCE_USDM if is_usd_margined else Venue.BINANCE_COINM,
            logger=logger,
            load_secrets=load_secrets,
        )
        self.key, self.secret = _resolve_secrets(self.load_secrets, key, secret)
        self.base_url = self.BASE_URLS[self.venue]

        # WebSocket connection state
        self.ws: aiohttp.ClientWebSocketResponse | None = None
        self.is_active = False
        self.last_used = 0

        # Request tracking
        self.pending_requests: dict[str, asyncio.Future] = {}
        self.request_id_counter = 0

        # Background tasks
        self.listener_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

        # Configuration
        self.heartbeat_interval = 30.0  # Binance requires heartbeat every 30s
        self.reconnect_base_delay = 0.25
        self.reconnect_max_delay = 2.0

        # JSON encoder/decoder
        self.json_encoder = msgspec.json.Encoder()
        self.json_decoder = msgspec.json.Decoder()

    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        self.request_id_counter += 1
        return f"{time_ms()}_{self.request_id_counter}"

    def _sign_params(self, params: dict) -> str:
        """Generate signature for WebSocket authentication."""
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        return hmac.new(
            key=self.secret.encode("utf-8"),
            msg=query_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    async def authenticate(self, ws: aiohttp.ClientWebSocketResponse) -> bool:
        """Authenticate the WebSocket connection.

        Args:
            ws (aiohttp.ClientWebSocketResponse): WebSocket connection.

        Returns:
            bool: True if authentication successful, False otherwise.

        """
        try:
            # Generate authentication parameters
            timestamp = time_ms()
            params = {
                "apiKey": self.key,
                "timestamp": timestamp,
            }
            signature = self._sign_params(params)
            params["signature"] = signature

            # Send authentication request
            auth_msg = {
                "id": self._generate_request_id(),
                "method": "auth",
                "params": params,
            }

            await ws.send_str(self.json_encoder.encode(auth_msg).decode())

            # Wait for authentication response
            auth_response = await ws.receive()
            if auth_response.type == aiohttp.WSMsgType.TEXT:
                resp = self.json_decoder.decode(auth_response.data)
                if (
                    resp.get("status") == 200
                    and resp.get("result", {}).get("status") == "AUTHENTICATED"
                ):
                    self.logger.debug("Binance WebSocket authentication successful")
                    return True
                else:
                    self.logger.error(
                        f"Binance WebSocket authentication failed: {resp}"
                    )
                    return False
            else:
                self.logger.error(
                    "Binance WebSocket authentication failed: No valid TEXT response"
                )
                return False

        except Exception as e:
            self.logger.error(f"Binance WebSocket authentication error: {e}")
            return False

    async def heartbeat(self):
        """Send a heartbeat ping to keep the connection alive."""
        if self.is_active and self.ws and not self.ws.closed:
            ping_msg = {"id": self._generate_request_id(), "method": "ping"}
            try:
                await self.ws.send_bytes(self.json_encoder.encode(ping_msg))
                self.logger.debug("Binance WebSocket ping sent")
            except Exception as e:
                self.logger.error(f"Binance WebSocket ping failed: {e}")
                await self._reconnect()

    async def _create_connection(self) -> aiohttp.ClientWebSocketResponse | None:
        """Create and authenticate a new WebSocket connection.

        Returns:
            Optional[aiohttp.ClientWebSocketResponse]: The authenticated WebSocket or None if failed.

        """
        try:
            ws = await self.session.ws_connect(self.base_url)
            authenticated = await self.authenticate(ws)
            if authenticated:
                self.logger.debug(
                    "Binance WebSocket connection created and authenticated"
                )
                return ws
            else:
                await ws.close()
                return None
        except Exception as e:
            self.logger.error(f"Binance WebSocket connection creation failed: {e}")
            return None

    async def connect(self):
        """Establish WebSocket connection and start background tasks."""
        try:
            self.ws = await self._create_connection()
            if self.ws:
                self.is_active = True
                self.last_used = time_ms()
                self.listener_task = asyncio.create_task(self._ws_listener())
                self.logger.info("Binance WebSocket connection established")
                self.is_running = True
            else:
                self.logger.error(
                    "Binance WebSocket connection failed to authenticate or create"
                )
                raise ConnectionError("Could not establish WebSocket connection")
        except Exception as e:
            self.logger.error(f"Binance WebSocket connection establishment failed: {e}")
            raise ConnectionError(f"Could not establish WebSocket connection: {e}")

        # Start the heartbeat task
        if self.heartbeat_task is None:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.logger.debug("Binance WebSocket heartbeat task started")

    async def _ws_listener(self):
        """Listen for messages on the WebSocket connection."""
        while self.is_running:
            try:
                if not self.ws or self.ws.closed:
                    await self._reconnect()
                    continue

                msg = await self.ws.receive()

                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = self.json_decoder.decode(msg.data)
                    await self._handle_message(data)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    self.logger.warning("Binance WebSocket connection closed")
                    await self._reconnect()
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    self.logger.error("Binance WebSocket connection error")
                    await self._reconnect()

            except asyncio.CancelledError:
                self.logger.debug("Binance WebSocket listener task cancelled")
                if self.ws:
                    try:
                        await self.ws.close()
                    except Exception as exc:
                        self.logger.error(
                            f"Binance WebSocket connection close failed: {exc}"
                        )
                return
            except Exception as e:
                self.logger.error(f"Binance WebSocket unexpected error: {e}")
                await self._reconnect()

    async def _handle_message(self, data: dict):
        """Handle incoming WebSocket messages."""
        msg_id = data.get("id")

        # Handle ping responses
        if data.get("method") == "pong":
            self.logger.debug("Binance WebSocket pong received")
            return

        # Handle request responses
        if msg_id and msg_id in self.pending_requests:
            future = self.pending_requests.pop(msg_id)
            if not future.done():
                future.set_result(data)
            return

        # Handle other messages (order updates, etc.)
        self.logger.debug(f"Binance WebSocket message received: {data}")

    async def _heartbeat_loop(self):
        """Periodically send heartbeat messages to keep connection alive."""
        while self.is_running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self.heartbeat()
            except asyncio.CancelledError:
                self.logger.debug("Binance WebSocket heartbeat task cancelled")
                return
            except Exception as e:
                self.logger.error(f"Binance WebSocket heartbeat loop error: {e}")

    async def _reconnect(self):
        """Reconnect the WebSocket connection with exponential backoff."""
        self.is_active = False
        delay = self.reconnect_base_delay
        max_retries = 5

        for attempt in range(max_retries):
            try:
                self.logger.info(
                    f"Binance WebSocket reconnecting (attempt {attempt + 1}/{max_retries})"
                )

                if self.ws:
                    await self.ws.close()

                await asyncio.sleep(delay)

                self.ws = await self._create_connection()
                if self.ws:
                    self.is_active = True
                    self.last_used = time_ms()
                    self.logger.info("Binance WebSocket reconnection successful")
                    return

                delay = min(delay * 2, self.reconnect_max_delay)

            except Exception as e:
                self.logger.error(
                    f"Binance WebSocket reconnection attempt {attempt + 1} failed: {e}"
                )
                delay = min(delay * 2, self.reconnect_max_delay)

        self.logger.error(
            f"Binance WebSocket reconnection failed after {max_retries} attempts"
        )

    async def submit[T](
        self, data: dict[str, Any], decoder: msgspec.json.Decoder[T]
    ) -> ClientResponse[T]:
        """Submit a request over the WebSocket connection."""
        started_ns = time_ns()
        operation = str(data.get("method", "unknown"))
        if not self.is_running:
            self.logger.error("Binance WebSocket client not initialized")
            return self.make_failure(
                meta=self.make_meta(
                    transport=ClientResponseTransport.WS,
                    operation=operation,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    attempt=1,
                ),
                err_no=1,
                err_msg="Client not initialized",
            )

        if not self.is_active or self.ws is None:
            self.logger.error(
                f"Binance WebSocket no active connection available; payload: {data}"
            )
            return self.make_failure(
                meta=self.make_meta(
                    transport=ClientResponseTransport.WS,
                    operation=operation,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    attempt=1,
                ),
                err_no=1,
                err_msg="No active connection",
            )

        # Add request ID and timestamp if not present
        data["id"] = self._generate_request_id()
        data["timestamp"] = time_ms()

        req_id = data["id"]
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self.pending_requests[req_id] = future
        try:
            await self.ws.send_bytes(self.json_encoder.encode(data))
            response = await asyncio.wait_for(future, timeout=5.0)
            status_code = response.get("status")
            meta = self.make_meta(
                transport=ClientResponseTransport.WS,
                operation=operation,
                started_ns=started_ns,
                finished_ns=time_ns(),
                request_id=req_id,
                status_code=int(status_code) if status_code is not None else None,
                attempt=1,
            )

            if response.get("status") == 200:
                return self.make_success(
                    data=decoder.decode(response.get("result", response)),
                    meta=meta,
                )
            else:
                error_msg = response.get("error", {}).get("msg", "Unknown error")
                error_code = response.get("error", {}).get("code", 1)
                self.logger.debug(
                    f"{self.__class__.__name__} request failed: {response}"
                )
                return self.make_failure(
                    meta=meta,
                    err_no=error_code,
                    err_msg=error_msg,
                )

        except TimeoutError:
            self.pending_requests.pop(req_id, None)
            self.logger.error(f"{self.__class__.__name__} request timeout")
            return self.make_failure(
                meta=self.make_meta(
                    transport=ClientResponseTransport.WS,
                    operation=operation,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    request_id=req_id,
                    attempt=1,
                    timeout=True,
                ),
                err_no=1,
                err_msg="Request timeout",
            )
        except Exception as e:
            self.pending_requests.pop(req_id, None)
            self.logger.error(f"{self.__class__.__name__} request send failed: {e}")
            return self.make_failure(
                meta=self.make_meta(
                    transport=ClientResponseTransport.WS,
                    operation=operation,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    request_id=req_id,
                    attempt=1,
                    timeout=isinstance(e, asyncio.TimeoutError),
                ),
                err_no=1,
                err_msg=str(e),
            )

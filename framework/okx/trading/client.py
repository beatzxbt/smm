"""OKX HTTP and WebSocket trading clients.

This module provides HTTP and WebSocket clients for OKX V5 API, handling
authentication, request signing, and communication with OKX trading endpoints.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
from datetime import datetime, timezone
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


RECV_WINDOW_MS = 5000
WS_PRIVATE_URL = "wss://ws.okx.com:8443/ws/v5/private"


class OkxHttpClient(HttpClient):
    """HTTP API client for OKX V5 (linear perpetuals).

    Handles REST API requests with OKX-specific authentication and signing.
    Uses ISO8601 timestamps and requires API key, secret, and passphrase.

    Docs: https://www.okx.com/docs-v5/en/#rest-api-authentication
    """

    BASE_URL = "https://www.okx.com"

    def __init__(
        self,
        logger: Logger,
        load_secrets: bool = False,
    ):
        """Initialize OKX HTTP client.

        Args:
            logger: Logger instance for client events.
            load_secrets: Whether to load credentials from environment.
        """
        super().__init__(venue=Venue.OKX, logger=logger, load_secrets=load_secrets)
        if self.load_secrets:
            self.key = Secret.load("OKX_KEY").value
            self.secret = Secret.load("OKX_SECRET").value
            self.passphrase = Secret.load("OKX_PASSPHRASE").value
        else:
            self.key = ""
            self.secret = ""
            self.passphrase = ""

    def sign(self, method: HttpMethod, endpoint: str, body: dict) -> dict:
        """Generate OK-ACCESS-* headers for signed requests.

        OKX signing: sign = Base64(HMAC_SHA256(timestamp + method + requestPath + body, secret))
        where timestamp is ISO8601 UTC format (e.g., 2020-12-08T09:08:57.715Z).

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path (e.g., /api/v5/trade/order).
            body: Request body data as dict.

        Returns:
            Dict of headers including signature and authentication.
        """
        timestamp = (
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        )
        payload = self._json_encoder.encode(body).decode() if body else ""

        # Prehash: timestamp + method + requestPath + body
        prehash = f"{timestamp}{method.value}{endpoint}{payload}"

        signature = base64.b64encode(
            hmac.new(
                key=self.secret.encode("utf-8"),
                msg=prehash.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
        ).decode()

        return {
            "OK-ACCESS-KEY": self.key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

    async def request[T](
        self,
        method: HttpMethod,
        endpoint: str,
        params: dict,
        data: dict,
        sign: bool,
        decoder: msgspec.json.Decoder[T],
    ) -> ClientResponse[T]:
        """Send an HTTP request to OKX API.

        Args:
            method: HTTP method.
            endpoint: API endpoint path.
            params: Query parameters for GET requests.
            data: Body data for POST/PUT requests.
            sign: Whether to sign the request with authentication.
            decoder: msgspec decoder for response data.

        Returns:
            ClientResponse with typed data or error information.
        """
        started_ns = time_ns()
        url = endpoint if endpoint.startswith("http") else self.BASE_URL + endpoint
        headers: Optional[dict[str, str]] = None
        json_payload: Optional[str] = None

        if method == HttpMethod.GET:
            if sign:
                headers = self.sign(method, endpoint, {})
        else:
            json_payload = self._json_encoder.encode(data or {}).decode()
            if sign:
                headers = self.sign(method, endpoint, data or {})

        try:
            async with self.session.request(
                method=method.value,
                url=url,
                params=params or None,
                data=json_payload if json_payload else None,
                headers=headers,
                timeout=RECV_WINDOW_MS / 1000,
            ) as resp:
                resp.raise_for_status()
                raw = await resp.read()
                payload = msgspec.json.decode(raw)
                status_code = resp.status

                # OKX response format: {"code": "0", "msg": "", "data": [...]}
                code = payload.get("code", "1")
                meta = self.make_meta(
                    transport=ClientResponseTransport.HTTP,
                    operation=endpoint,
                    started_ns=started_ns,
                    finished_ns=time_ns(),
                    status_code=status_code,
                    attempt=1,
                )
                if code == "0":
                    result = payload.get("data", payload)
                    return self.make_success(
                        data=decoder.decode(self._json_encoder.encode(result)),
                        meta=meta,
                    )
                return self.make_failure(
                    meta=meta,
                    err_no=int(code),
                    err_msg=str(payload.get("msg", "Unknown error")),
                )
        except Exception as e:
            self.logger.warning(f"{self.__class__.__name__}.request error; {e}")
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


class OkxWsClient(WsClient):
    """WebSocket API client for OKX V5 private trade stream.

    Handles WebSocket connections for trading operations with OKX-specific
    authentication using API key, secret, and passphrase.

    Docs: https://www.okx.com/docs-v5/en/#websocket-api-login
    """

    def __init__(
        self,
        logger: Logger,
        load_secrets: bool = False,
    ):
        """Initialize OKX WebSocket client.

        Args:
            logger: Logger instance for client events.
            load_secrets: Whether to load credentials from environment.
        """
        super().__init__(venue=Venue.OKX, logger=logger, load_secrets=load_secrets)
        if self.load_secrets:
            self.key = Secret.load("OKX_KEY").value
            self.secret = Secret.load("OKX_SECRET").value
            self.passphrase = Secret.load("OKX_PASSPHRASE").value
        else:
            self.key = ""
            self.secret = ""
            self.passphrase = ""
        self.base_url = WS_PRIVATE_URL

        self.ws: aiohttp.ClientWebSocketResponse | None = None
        self.is_active = False
        self.last_used = 0

        self.pending_requests: dict[str, asyncio.Future] = {}
        self.request_id_counter = 0

        self.listener_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.heartbeat_interval = 15.0  # OKX recommends 15s

        self.json_encoder = msgspec.json.Encoder()
        self.json_decoder = msgspec.json.Decoder()

    def _generate_request_id(self) -> str:
        """Generate unique request ID for tracking WebSocket requests.

        Returns:
            Unique request ID string.
        """
        self.request_id_counter += 1
        return f"{time_ns()}_{self.request_id_counter}"

    async def authenticate(self, ws: aiohttp.ClientWebSocketResponse) -> bool:
        """Authenticate WebSocket connection with OKX.

        OKX WS auth: sign = Base64(HMAC_SHA256(timestamp + "GET" + "/users/self/verify", secret))
        where timestamp is unix epoch seconds as string.

        Args:
            ws: WebSocket connection to authenticate.

        Returns:
            True if authentication successful, False otherwise.
        """
        try:
            timestamp = str(int(time_ms() / 1000))
            prehash = f"{timestamp}GET/users/self/verify"
            signature = base64.b64encode(
                hmac.new(
                    key=self.secret.encode("utf-8"),
                    msg=prehash.encode("utf-8"),
                    digestmod=hashlib.sha256,
                ).digest()
            ).decode()

            auth_msg = {
                "op": "login",
                "args": [
                    {
                        "apiKey": self.key,
                        "passphrase": self.passphrase,
                        "timestamp": timestamp,
                        "sign": signature,
                    }
                ],
            }
            await ws.send_str(self.json_encoder.encode(auth_msg).decode("utf-8"))
            auth_response = await ws.receive()

            if auth_response.type == aiohttp.WSMsgType.TEXT:
                resp = self.json_decoder.decode(auth_response.data)
                # OKX auth response: {"event": "login", "code": "0", "msg": ""}
                return resp.get("code", "1") == "0"
            return False
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__}.authenticate error; {e}")
            return False

    async def heartbeat(self):
        """Send heartbeat ping to maintain connection.

        OKX expects periodic pings to keep connection alive.
        """
        if self.is_active and self.ws and not self.ws.closed:
            try:
                ping_msg = {"op": "ping"}
                await self.ws.send_str(
                    self.json_encoder.encode(ping_msg).decode("utf-8")
                )
            except Exception as e:
                self.logger.error(f"{self.__class__.__name__}.heartbeat error; {e}")

    async def connect(self):
        """Connect to OKX WebSocket and authenticate.

        Raises:
            ConnectionError: If connection or authentication fails.
        """
        try:
            self.ws = await self.session.ws_connect(self.base_url)
            if not await self.authenticate(self.ws):
                raise ConnectionError("OKX WebSocket authentication failed")
            self.is_active = True
            self.last_used = time_ms()
            self.listener_task = asyncio.create_task(self._ws_listener())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.is_running = True
            self.logger.info(
                f"{self.__class__.__name__}.connect connected and authenticated"
            )
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__}.connect error; {e}")
            raise

    async def _ws_listener(self):
        """Listen for incoming WebSocket messages and route to pending requests."""
        while self.is_running:
            try:
                if not self.ws or self.ws.closed:
                    break
                msg = await self.ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = self.json_decoder.decode(msg.data)

                    # Handle pong responses
                    if data.get("event") == "pong":
                        continue

                    # Route responses by request ID
                    req_id = data.get("id")
                    if req_id and req_id in self.pending_requests:
                        fut = self.pending_requests.pop(req_id)
                        if not fut.done():
                            fut.set_result(data)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"{self.__class__.__name__}._ws_listener error; {e}")
                break

    async def _heartbeat_loop(self):
        """Periodically send heartbeat pings."""
        while self.is_running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self.heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"{self.__class__.__name__}._heartbeat_loop error; {e}"
                )

    async def submit[T](
        self, data: dict[str, Any], decoder: msgspec.json.Decoder[T]
    ) -> ClientResponse[T]:
        """Submit a trading request via WebSocket.

        Args:
            data: Request data including "op" and "args" fields.
            decoder: msgspec decoder for response data.

        Returns:
            ClientResponse with typed data or error information.
        """
        started_ns = time_ns()
        operation = str(data.get("op", "unknown"))
        if not self.is_running or not self.is_active or self.ws is None:
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

        data["id"] = self._generate_request_id()
        req_id = data["id"]
        future = asyncio.get_running_loop().create_future()
        self.pending_requests[req_id] = future

        try:
            await self.ws.send_str(self.json_encoder.encode(data).decode("utf-8"))
            resp = await asyncio.wait_for(future, timeout=5.0)

            # OKX response: {"id": "req123", "op": "order", "code": "0", "data": [...], "msg": ""}
            code = resp.get("code", "1")
            status_code = int(code)
            meta = self.make_meta(
                transport=ClientResponseTransport.WS,
                operation=operation,
                started_ns=started_ns,
                finished_ns=time_ns(),
                request_id=req_id,
                status_code=status_code,
                attempt=1,
            )
            if code == "0":
                result_payload = resp.get("data", resp)
                return self.make_success(
                    data=decoder.decode(self._json_encoder.encode(result_payload)),
                    meta=meta,
                )
            return self.make_failure(
                meta=meta,
                err_no=status_code,
                err_msg=str(resp.get("msg", "Unknown error")),
            )
        except Exception as e:
            self.pending_requests.pop(req_id, None)
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

    async def close(self):
        """Close WebSocket connection and cleanup resources."""
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
        if self.listener_task and not self.listener_task.done():
            self.listener_task.cancel()
        if self.ws and not self.ws.closed:
            await self.ws.close()
        await super().close()
        self.is_active = False

import asyncio
import hashlib
import hmac
from typing import Any, Optional

import aiohttp
import msgspec

from framework.base.common import Venue
from mm_toolbox.logging.standard import Logger
from mm_toolbox.time import time_ms, time_ns
from framework.base.trading.client import HttpClient, HttpMethod, WsClient
from framework.base.trading.models import Secret
from framework.base.trading.models import (
    ClientResponse,
    ClientResponseFailure,
    ClientResponseSuccess,
)


RECV_WINDOW_MS = 5000
WS_PRIVATE_URL = "wss://stream.bybit.com/v5/private"


def _resolve_secrets(
    load_secrets: bool, key: str | None, secret: str | None
) -> tuple[str, str]:
    if load_secrets:
        return (
            Secret.load("BYBIT_KEY").value,
            Secret.load("BYBIT_SECRET").value,
        )
    return (key or ""), (secret or "")


class BybitHttpClient(HttpClient):
    """HTTP API client for Bybit V5 (linear)."""

    BASE_URL = "https://api.bybit.com"

    def __init__(
        self,
        logger: Logger,
        load_secrets: bool = False,
        key: str | None = None,
        secret: str | None = None,
    ):
        super().__init__(venue=Venue.BYBIT, logger=logger, load_secrets=load_secrets)
        self.key, self.secret = _resolve_secrets(self.load_secrets, key, secret)

    def sign(self, method: HttpMethod, endpoint: str, body: dict) -> dict:
        """Generate X-BAPI-* headers for signed requests.

        Bybit V5 signing: sign = HMAC_SHA256(secret, timestamp + apiKey + recvWindow + body)
        where body is the exact POST body or empty string for GET.
        """
        timestamp = str(time_ms())
        recv_window = str(RECV_WINDOW_MS)
        payload = msgspec.json.encode(body).decode() if body else ""
        signature = hmac.new(
            key=self.secret.encode("utf-8"),
            msg=f"{timestamp}{self.key}{recv_window}{payload}".encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return {
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-API-KEY": self.key,
            "X-BAPI-RECV-WINDOW": recv_window,
            "X-BAPI-SIGN": signature,
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
        url = endpoint if endpoint.startswith("http") else self.BASE_URL + endpoint
        headers: Optional[dict[str, str]] = None
        json_payload: Optional[str] = None

        if method == HttpMethod.GET:
            # Bybit signs GET with empty body; params go in query string
            if params:
                # aiohttp will handle params separately
                pass
            if sign:
                headers = self.sign(method, endpoint, {})
        else:
            json_payload = msgspec.json.encode(data or {}).decode()
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
                # Expect retCode/retMsg style
                ret_code = payload.get("retCode", 0)
                if ret_code == 0:
                    result = payload.get("result", payload)
                    return ClientResponseSuccess[T](
                        is_successful=True,
                        err_no=0,
                        err_msg="",
                        data=decoder.decode(msgspec.json.encode(result)),
                    )
                return ClientResponseFailure(
                    is_successful=False,
                    err_no=int(ret_code),
                    err_msg=str(payload.get("retMsg", "Unknown error")),
                    data=None,
                )
        except Exception as e:
            self.logger.warning(f"{self.__class__.__name__} request error: {e}")
            return ClientResponseFailure(
                is_successful=False, err_no=1, err_msg=str(e), data=None
            )


class BybitWsClient(WsClient):
    """WebSocket API client for Bybit V5 private trade stream."""

    def __init__(
        self,
        logger: Logger,
        load_secrets: bool = False,
        key: str | None = None,
        secret: str | None = None,
    ):
        super().__init__(venue=Venue.BYBIT, logger=logger, load_secrets=load_secrets)
        self.key, self.secret = _resolve_secrets(self.load_secrets, key, secret)
        self.base_url = WS_PRIVATE_URL

        self.ws: aiohttp.ClientWebSocketResponse | None = None
        self.is_active = False
        self.last_used = 0

        self.pending_requests: dict[str, asyncio.Future] = {}
        self.request_id_counter = 0

        self.listener_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.heartbeat_interval = 10.0

        self.json_encoder = msgspec.json.Encoder()
        self.json_decoder = msgspec.json.Decoder()

    def _generate_request_id(self) -> str:
        self.request_id_counter += 1
        return f"{time_ns()}_{self.request_id_counter}"

    async def authenticate(self, ws: aiohttp.ClientWebSocketResponse) -> bool:
        try:
            expire = str(int(time_ms() + 60_000))
            signature = hmac.new(
                key=self.secret.encode("utf-8"),
                msg=f"GET/realtime{expire}".encode("utf-8"),
                digestmod=hashlib.sha256,
            ).hexdigest()
            auth_msg = {"op": "auth", "args": [self.key, expire, signature]}
            await ws.send_bytes(self.json_encoder.encode(auth_msg))
            auth_response = await ws.receive()
            if auth_response.type == aiohttp.WSMsgType.TEXT:
                resp = self.json_decoder.decode(auth_response.data)
                return resp.get("retCode", 1) == 0
            return False
        except Exception as e:
            self.logger.error(f"Bybit WebSocket authentication error: {e}")
            return False

    async def heartbeat(self):
        if self.is_active and self.ws and not self.ws.closed:
            try:
                ping_msg = {"op": "ping", "reqId": self._generate_request_id()}
                await self.ws.send_bytes(self.json_encoder.encode(ping_msg))
            except Exception as e:
                self.logger.error(f"Bybit WebSocket ping failed: {e}")

    async def connect(self):
        try:
            self.ws = await self.session.ws_connect(self.base_url)
            if not await self.authenticate(self.ws):
                raise ConnectionError("Bybit WebSocket authentication failed")
            self.is_active = True
            self.last_used = time_ms()
            self.listener_task = asyncio.create_task(self._ws_listener())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.is_running = True
        except Exception as e:
            self.logger.error(f"Bybit WebSocket connection failed: {e}")
            raise

    async def _ws_listener(self):
        while self.is_running:
            try:
                if not self.ws or self.ws.closed:
                    break
                msg = await self.ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = self.json_decoder.decode(msg.data)
                    req_id = data.get("reqId") or data.get("id")
                    if req_id and req_id in self.pending_requests:
                        fut = self.pending_requests.pop(req_id)
                        if not fut.done():
                            fut.set_result(data)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Bybit WebSocket listener error: {e}")
                break

    async def _heartbeat_loop(self):
        while self.is_running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self.heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Bybit WebSocket heartbeat error: {e}")

    async def submit[T](
        self, data: dict[str, Any], decoder: msgspec.json.Decoder[T]
    ) -> ClientResponse[T]:
        if not self.is_running or not self.is_active or self.ws is None:
            return ClientResponseFailure(
                is_successful=False, err_no=1, err_msg="No active connection", data=None
            )

        data["reqId"] = self._generate_request_id()
        req_id = data["reqId"]
        future = asyncio.get_event_loop().create_future()
        self.pending_requests[req_id] = future

        try:
            await self.ws.send_bytes(self.json_encoder.encode(data))
            resp = await asyncio.wait_for(future, timeout=5.0)
            if resp.get("retCode", 1) == 0:
                result_payload = resp.get("result", resp)
                return ClientResponseSuccess[T](
                    is_successful=True,
                    err_no=0,
                    err_msg="",
                    data=decoder.decode(msgspec.json.encode(result_payload)),
                )
            return ClientResponseFailure(
                is_successful=False,
                err_no=int(resp.get("retCode", 1)),
                err_msg=str(resp.get("retMsg", "Unknown error")),
                data=None,
            )
        except Exception as e:
            self.pending_requests.pop(req_id, None)
            return ClientResponseFailure(
                is_successful=False, err_no=1, err_msg=str(e), data=None
            )

    async def close(self):
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
        if self.listener_task and not self.listener_task.done():
            self.listener_task.cancel()
        if self.ws and not self.ws.closed:
            await self.ws.close()
        await self.session.close()
        self.is_running = False
        self.is_active = False

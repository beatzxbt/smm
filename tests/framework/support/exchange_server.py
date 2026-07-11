"""Deterministic localhost HTTP/WebSocket exchange simulator."""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

import msgspec
from aiohttp import WSMsgType, web
from mm_toolbox.ringbuffer import GenericRingBuffer


async def collect_messages(
    buffer: GenericRingBuffer,
    expected: int,
    timeout_s: float = 2.0,
    settle_turns: int = 0,
) -> list[object]:
    """Collect at least ``expected`` messages with bounded deterministic waits."""
    messages: list[object] = []
    try:
        async with asyncio.timeout(timeout_s):
            while len(messages) < expected:
                while not buffer.is_empty() and len(messages) < expected:
                    messages.append(buffer.consume())
                if len(messages) < expected:
                    await asyncio.sleep(0)
    except TimeoutError as exc:
        counts = Counter(type(message).__name__ for message in messages)
        raise AssertionError(
            f"received {len(messages)}/{expected} messages: {dict(counts)}"
        ) from exc

    for _ in range(settle_turns):
        await asyncio.sleep(0)
        while not buffer.is_empty():
            messages.append(buffer.consume())
    return messages


class ScriptedExchangeServer:
    """Serve scripted exchange traffic over real localhost transports."""

    def __init__(self) -> None:
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._http: dict[tuple[str, str], deque[tuple[int, bytes]]] = defaultdict(deque)
        self._websockets: set[web.WebSocketResponse] = set()
        self._subscriptions: dict[web.WebSocketResponse, set[str]] = defaultdict(set)
        self._ws_responses: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
        self._ws_pushes: dict[str, tuple[str, dict[str, Any]]] = {}
        self.http_requests: list[dict[str, Any]] = []
        self.ws_frames: list[Any] = []
        self.port = 0

    @property
    def http_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def ws_url(self) -> str:
        return f"ws://127.0.0.1:{self.port}/ws"

    @property
    def subscriptions(self) -> set[str]:
        return (
            set().union(*self._subscriptions.values()) if self._subscriptions else set()
        )

    @property
    def websocket_count(self) -> int:
        return len(self._websockets)

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/ws", self._handle_ws)
        app.router.add_get("/ws/{tail:.*}", self._handle_ws)
        app.router.add_route("*", "/{tail:.*}", self._handle_http)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await self._site.start()
        server = self._site._server
        if server is None or not server.sockets:
            raise RuntimeError("Scenario server failed to bind")
        self.port = int(server.sockets[0].getsockname()[1])

    async def close(self) -> None:
        for ws in tuple(self._websockets):
            await ws.close()
        self._websockets.clear()
        if self._runner is not None:
            await self._runner.cleanup()
        self._runner = None
        self._site = None

    def add_http_response(
        self,
        method: str,
        path: str,
        body: bytes | dict[str, Any] | list[Any],
        status: int = 200,
    ) -> None:
        payload = body if isinstance(body, bytes) else msgspec.json.encode(body)
        self._http[(method.upper(), path)].append((status, payload))

    def add_ws_response(self, operation: str, body: dict[str, Any]) -> None:
        self._ws_responses[operation].append(body)

    def load_jsonl(self, path: Path) -> None:
        for raw_line in path.read_bytes().splitlines():
            if not raw_line.strip():
                continue
            record = msgspec.json.decode(raw_line)
            if record["kind"] == "http":
                self.add_http_response(
                    record["method"],
                    record["path"],
                    record["body"],
                    int(record.get("status", 200)),
                )
            elif record["kind"] == "ws_response":
                self.add_ws_response(record["operation"], record["body"])
            elif record["kind"] == "ws_push":
                self._ws_pushes[record["name"]] = (
                    record["subscription"],
                    record["body"],
                )
            else:
                raise ValueError(f"Unsupported transcript record: {record['kind']}")

    async def wait_for_ws_frames(self, count: int, timeout_s: float = 2.0) -> None:
        async with asyncio.timeout(timeout_s):
            while len(self.ws_frames) < count:
                await asyncio.sleep(0)
            # The frame is recorded before its subscription state is applied.
            # Yield once so callers can safely send traffic for that subscription.
            await asyncio.sleep(0)

    async def wait_for_websockets(self, count: int, timeout_s: float = 2.0) -> None:
        async with asyncio.timeout(timeout_s):
            while len(self._websockets) < count:
                await asyncio.sleep(0)

    async def broadcast(self, payload: bytes | dict[str, Any]) -> None:
        data = payload if isinstance(payload, bytes) else msgspec.json.encode(payload)
        for ws in tuple(self._websockets):
            if not ws.closed:
                await ws.send_str(data.decode())

    async def send_to_subscribers(
        self, topic: str, payload: bytes | dict[str, Any]
    ) -> None:
        data = payload if isinstance(payload, bytes) else msgspec.json.encode(payload)
        for ws, subscriptions in tuple(self._subscriptions.items()):
            if not ws.closed and topic in subscriptions:
                await ws.send_str(data.decode())

    async def push(self, name: str) -> None:
        subscription, body = self._ws_pushes[name]
        if subscription == "*":
            await self.broadcast(body)
        else:
            await self.send_to_subscribers(subscription, body)

    async def disconnect_websockets(self) -> None:
        for ws in tuple(self._websockets):
            await ws.close()

    async def _handle_http(self, request: web.Request) -> web.Response:
        raw = await request.read()
        self.http_requests.append(
            {
                "method": request.method,
                "path": request.path,
                "query": dict(request.query),
                "headers": dict(request.headers),
                "body": raw,
            }
        )
        responses = self._http[(request.method, request.path)]
        if not responses:
            return web.json_response({"error": "unscripted request"}, status=500)
        status, body = responses.popleft()
        return web.Response(status=status, body=body, content_type="application/json")

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._websockets.add(ws)
        streams = request.query.get("streams", "")
        if streams:
            self._subscriptions[ws].update(streams.split("/"))
        try:
            async for message in ws:
                if message.type in (WSMsgType.TEXT, WSMsgType.BINARY):
                    raw = message.data
                    if isinstance(raw, str):
                        raw = raw.encode()
                    try:
                        decoded = msgspec.json.decode(raw)
                        self.ws_frames.append(decoded)
                        if isinstance(decoded, dict):
                            args = decoded.get("args", decoded.get("params", []))
                            operation = str(
                                decoded.get("op", decoded.get("method", ""))
                            ).lower()
                            if operation == "subscribe":
                                self._subscriptions[ws].update(
                                    self._subscription_key(arg) for arg in args
                                )
                            elif operation == "unsubscribe":
                                self._subscriptions[ws].difference_update(
                                    self._subscription_key(arg) for arg in args
                                )
                            responses = self._ws_responses[operation]
                            if responses:
                                response = msgspec.json.decode(
                                    msgspec.json.encode(responses.popleft())
                                )
                                request_id = decoded.get("reqId", decoded.get("id"))
                                if request_id is not None:
                                    if "reqId" in decoded:
                                        response.setdefault("reqId", request_id)
                                    else:
                                        response.setdefault("id", request_id)
                                await ws.send_str(
                                    msgspec.json.encode(response).decode()
                                )
                    except msgspec.DecodeError:
                        self.ws_frames.append(raw)
        finally:
            self._websockets.discard(ws)
            self._subscriptions.pop(ws, None)
        return ws

    @staticmethod
    def _subscription_key(arg: Any) -> str:
        if isinstance(arg, dict):
            return f"{arg.get('channel', '')}:{arg.get('instId', '')}"
        return str(arg)

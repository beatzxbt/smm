import asyncio

from framework.base.tools.websocket import (
    AuthenticationStrategy,
    WebsocketConnection,
)


class AcceptAuth(AuthenticationStrategy):
    async def authenticate(self, ws) -> bool:  # type: ignore[override]
        return True


class RejectAuth(AuthenticationStrategy):
    async def authenticate(self, ws) -> bool:  # type: ignore[override]
        return False


class FakeWS:
    def __init__(self, messages: list[bytes] | None = None):
        self._messages = list(messages or [])
        self.sent: list[bytes] = []
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)

    async def send_bytes(self, data: bytes):
        self.sent.append(data)

    async def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, ws: FakeWS):
        self._ws = ws
        self.closed = False

    async def ws_connect(self, url: str):  # noqa: ARG002
        return self._ws

    async def close(self):  # pragma: no cover - cleanup path
        self.closed = True


def test_websocket_context_manager_and_iteration(monkeypatch):
    payloads = [b"sub1", b"sub2"]
    fake_ws = FakeWS(messages=[b"a", b"b", b"c"])

    async def fake_session_ctor(*args, **kwargs):  # noqa: ARG001
        return FakeSession(ws=fake_ws)

    monkeypatch.setattr(
        "framework.base.tools.websocket.aiohttp.ClientSession", fake_session_ctor
    )

    conn = WebsocketConnection(
        wss_url="wss://unit.test/ws",
        on_connect=payloads,
        auth_strategy=AcceptAuth(),
    )

    received: list[bytes] = []

    async def runner():
        async with conn as ws:
            assert ws.is_connected is True
            async for msg in ws:
                received.append(msg)

    asyncio.run(runner())

    assert fake_ws.sent == payloads
    assert received == [b"a", b"b", b"c"]
    assert conn.seq_id == 3
    assert conn.is_connected is False


def test_websocket_connect_calls_on_message(monkeypatch):
    payloads = [b"hello"]
    fake_ws = FakeWS(messages=[b"x", b"y"])  # iteration will end after 2 messages

    async def fake_session_ctor(*args, **kwargs):  # noqa: ARG001
        return FakeSession(ws=fake_ws)

    monkeypatch.setattr(
        "framework.base.tools.websocket.aiohttp.ClientSession", fake_session_ctor
    )

    conn = WebsocketConnection(
        wss_url="wss://unit.test/ws",
        on_connect=payloads,
        auth_strategy=AcceptAuth(),
    )

    seen: list[bytes] = []

    async def on_message(msg: bytes):
        seen.append(msg)

    asyncio.run(conn.connect(on_message=on_message))
    assert fake_ws.sent == payloads
    assert seen == [b"x", b"y"]
    assert conn.seq_id == 2


def test_websocket_authentication_failure_raises(monkeypatch):
    fake_ws = FakeWS(messages=[])

    async def fake_session_ctor(*args, **kwargs):  # noqa: ARG001
        return FakeSession(ws=fake_ws)

    monkeypatch.setattr(
        "framework.base.tools.websocket.aiohttp.ClientSession", fake_session_ctor
    )

    conn = WebsocketConnection(
        wss_url="wss://unit.test/ws",
        on_connect=[],
        auth_strategy=RejectAuth(),
    )

    async def runner():
        try:
            async with conn:
                pass
        except RuntimeError:
            return True
        return False

    assert asyncio.run(runner()) is True

"""
Tests for WebSocketConnection behavior.

Validates connection lifecycle, message iteration, and reconnection backoff.
"""

from __future__ import annotations


import aiohttp
import pytest

from framework.base.stream.connection import WebSocketConnection
from mm_toolbox.logging.standard import Logger


class FakeWSMessage:
    """Simple websocket message stub."""

    def __init__(self, msg_type: aiohttp.WSMsgType, data: bytes | str) -> None:
        """Initialize a fake websocket message.

        Args:
            msg_type: WebSocket message type.
            data: Message payload data.

        Returns:
            None.
        """
        self.type = msg_type
        self.data = data


class FakeWebSocket:
    """Async iterable websocket stub."""

    def __init__(self, messages: list[FakeWSMessage]) -> None:
        """Initialize the fake websocket.

        Args:
            messages (list[FakeWSMessage]): Messages to yield.

        Returns:
            None.
        """
        self._messages = list(messages)
        self.closed = False
        self.sent_bytes: list[bytes] = []
        self.sent_str: list[str] = []

    def __aiter__(self):
        """Return the async iterator.

        Returns:
            FakeWebSocket: Async iterator over websocket messages.
        """
        return self

    async def __anext__(self) -> FakeWSMessage:
        """Return the next message.

        Returns:
            FakeWSMessage: Next websocket message.
        """
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)

    async def close(self) -> None:
        """Close the websocket.

        Returns:
            None.
        """
        self.closed = True

    async def send_bytes(self, payload: bytes) -> None:
        """Capture binary payloads.

        Args:
            payload: Binary payload to record.

        Returns:
            None.
        """
        self.sent_bytes.append(payload)

    async def send_str(self, payload: str) -> None:
        """Capture text payloads.

        Args:
            payload: Text payload to record.

        Returns:
            None.
        """
        self.sent_str.append(payload)

    async def receive(self) -> FakeWSMessage:
        """Return the next message for receive().

        Returns:
            FakeWSMessage: Next websocket message or closed message.
        """
        if not self._messages:
            return FakeWSMessage(aiohttp.WSMsgType.CLOSED, b"")
        return self._messages.pop(0)


class FakeSession:
    """ClientSession stub returning a fixed websocket."""

    def __init__(self, ws: FakeWebSocket) -> None:
        """Initialize the fake session.

        Args:
            ws: Websocket instance to return.

        Returns:
            None.
        """
        self._ws = ws
        self.closed = False

    async def ws_connect(self, _url: str) -> FakeWebSocket:
        """Return the stubbed websocket.

        Args:
            _url: Websocket URL (unused).

        Returns:
            FakeWebSocket: Websocket instance.
        """
        return self._ws

    async def close(self) -> None:
        """Close the session.

        Returns:
            None.
        """
        self.closed = True


class TestWebSocketConnection:
    """WebSocketConnection behaviors."""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, monkeypatch) -> None:
        """Test connect/disconnect toggles connection state.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        ws = FakeWebSocket(messages=[])
        session = FakeSession(ws)
        monkeypatch.setattr(
            "framework.base.stream.connection.aiohttp.ClientSession",
            lambda: session,
        )

        connection = WebSocketConnection("wss://example", Logger(name="test"))
        await connection.connect()
        assert connection.is_connected is True

        await connection.disconnect()
        assert connection.is_connected is False
        assert session.closed is True

    @pytest.mark.asyncio
    async def test_message_iteration(self, monkeypatch) -> None:
        """Test async iteration yields normalized bytes.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        messages = [
            FakeWSMessage(aiohttp.WSMsgType.BINARY, b"one"),
            FakeWSMessage(aiohttp.WSMsgType.TEXT, "two"),
        ]
        ws = FakeWebSocket(messages=messages)
        session = FakeSession(ws)
        monkeypatch.setattr(
            "framework.base.stream.connection.aiohttp.ClientSession",
            lambda: session,
        )

        connection = WebSocketConnection(
            "wss://example", Logger(name="test"), auto_reconnect=False
        )
        await connection.connect()

        received = []
        async for msg in connection:
            received.append(msg)
        assert received == [b"one", b"two"]

    @pytest.mark.asyncio
    async def test_send_requires_connection(self) -> None:
        """Test send raises when not connected.

        Returns:
            None.
        """
        connection = WebSocketConnection("wss://example", Logger(name="test"))
        with pytest.raises(ConnectionError, match="not connected"):
            await connection.send("payload")

    @pytest.mark.asyncio
    async def test_send_text_and_binary(self, monkeypatch) -> None:
        """Test send normalizes text and binary payloads.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        ws = FakeWebSocket(messages=[])
        session = FakeSession(ws)
        monkeypatch.setattr(
            "framework.base.stream.connection.aiohttp.ClientSession",
            lambda: session,
        )

        connection = WebSocketConnection("wss://example", Logger(name="test"))
        await connection.connect()

        await connection.send("hello")
        await connection.send(b"raw-bytes")
        await connection.send("binary", as_binary=True)
        await connection.send(b"\x00\x01", as_binary=True)

        assert ws.sent_str == ["hello", "raw-bytes"]
        assert ws.sent_bytes == [b"binary", b"\x00\x01"]

    @pytest.mark.asyncio
    async def test_receive_requires_connection(self) -> None:
        """Test receive raises when not connected.

        Returns:
            None.
        """
        connection = WebSocketConnection("wss://example", Logger(name="test"))
        with pytest.raises(ConnectionError, match="not connected"):
            await connection.receive()

    @pytest.mark.asyncio
    async def test_receive_normalizes_payload(self, monkeypatch) -> None:
        """Test receive returns normalized bytes.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        ws = FakeWebSocket(
            messages=[FakeWSMessage(aiohttp.WSMsgType.TEXT, "payload")]
        )
        session = FakeSession(ws)
        monkeypatch.setattr(
            "framework.base.stream.connection.aiohttp.ClientSession",
            lambda: session,
        )

        connection = WebSocketConnection("wss://example", Logger(name="test"))
        await connection.connect()

        payload = await connection.receive()
        assert payload == b"payload"

    @pytest.mark.asyncio
    async def test_iteration_no_auto_reconnect(self, monkeypatch) -> None:
        """Test iteration stops when auto reconnect is disabled.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        connection = WebSocketConnection(
            "wss://example", Logger(name="test"), auto_reconnect=False
        )

        async def _fail_connect() -> None:
            """Always fail connect.

            Returns:
                None.
            """
            raise ConnectionError("fail")

        monkeypatch.setattr(connection, "connect", _fail_connect)

        received = []
        async for msg in connection:
            received.append(msg)

        assert received == []

    @pytest.mark.asyncio
    async def test_reconnect_triggers_callbacks(self, monkeypatch) -> None:
        """Test reconnect invokes callbacks after success.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        connection = WebSocketConnection("wss://example", Logger(name="test"))
        ws = FakeWebSocket(messages=[FakeWSMessage(aiohttp.WSMsgType.TEXT, "ok")])

        async def _fail_connect() -> None:
            """Always fail initial connect.

            Returns:
                None.
            """
            raise ConnectionError("fail")

        reconnect_calls = {"count": 0}

        async def _fake_reconnect() -> bool:
            """Succeed once, then stop reconnecting.

            Returns:
                bool: Whether reconnect succeeded.
            """
            reconnect_calls["count"] += 1
            if reconnect_calls["count"] == 1:
                connection._ws = ws
                connection._is_connected = True
                return True
            return False

        callbacks: list[str] = []

        async def _on_reconnect() -> None:
            """Capture reconnect callback invocation.

            Returns:
                None.
            """
            callbacks.append("called")

        connection.add_reconnect_callback(_on_reconnect)
        monkeypatch.setattr(connection, "connect", _fail_connect)
        monkeypatch.setattr(connection, "_reconnect_with_backoff", _fake_reconnect)

        received = []
        async for msg in connection:
            received.append(msg)

        assert received == [b"ok"]
        assert callbacks == ["called"]

    @pytest.mark.asyncio
    async def test_reconnect_backoff(self, monkeypatch) -> None:
        """Test reconnection backoff uses exponential delays.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        connection = WebSocketConnection("wss://example", Logger(name="test"))
        delays: list[float] = []

        async def _fake_sleep(delay: float) -> None:
            """Capture sleep delays for assertions.

            Args:
                delay: Sleep delay in seconds.

            Returns:
                None.
            """
            delays.append(delay)

        attempts = {"count": 0}

        async def _flaky_connect() -> None:
            """Fail twice then succeed.

            Returns:
                None.
            """
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ConnectionError("temporary failure")
            connection._is_connected = True

        monkeypatch.setattr(
            "framework.base.stream.connection.asyncio.sleep", _fake_sleep
        )
        monkeypatch.setattr(connection, "connect", _flaky_connect)

        result = await connection._reconnect_with_backoff()
        assert result is True
        assert delays == [1.0, 2.0, 4.0]

    @pytest.mark.asyncio
    async def test_reconnect_backoff_gives_up(self, monkeypatch) -> None:
        """Test reconnection stops after max attempts.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        connection = WebSocketConnection(
            "wss://example", Logger(name="test"), max_reconnect_attempts=2
        )
        delays: list[float] = []

        async def _fake_sleep(delay: float) -> None:
            """Capture sleep delays for assertions.

            Args:
                delay: Sleep delay in seconds.

            Returns:
                None.
            """
            delays.append(delay)

        async def _always_fail_connect() -> None:
            """Always fail connect.

            Returns:
                None.
            """
            raise ConnectionError("fail")

        monkeypatch.setattr(
            "framework.base.stream.connection.asyncio.sleep", _fake_sleep
        )
        monkeypatch.setattr(connection, "connect", _always_fail_connect)

        result = await connection._reconnect_with_backoff()
        assert result is False
        assert delays == [1.0, 2.0]

    def test_normalize_message_filters_non_payloads(self) -> None:
        """Test normalize filters unsupported message types.

        Returns:
            None.
        """
        connection = WebSocketConnection("wss://example", Logger(name="test"))
        connection._is_connected = True

        closed = FakeWSMessage(aiohttp.WSMsgType.CLOSED, b"")
        ping = FakeWSMessage(aiohttp.WSMsgType.PING, b"")

        assert connection._normalize_message(closed) is None
        assert connection._is_connected is False
        assert connection._normalize_message(ping) is None

    @pytest.mark.asyncio
    async def test_reconnect_callback_errors_do_not_stop(self) -> None:
        """Test reconnect callback errors are swallowed.

        Returns:
            None.
        """
        connection = WebSocketConnection("wss://example", Logger(name="test"))
        calls: list[str] = []

        async def _bad_callback() -> None:
            """Raise an error for testing.

            Returns:
                None.
            """
            raise RuntimeError("boom")

        async def _good_callback() -> None:
            """Record successful callback execution.

            Returns:
                None.
            """
            calls.append("ok")

        connection.add_reconnect_callback(_bad_callback)
        connection.add_reconnect_callback(_good_callback)

        await connection._notify_reconnect()
        assert calls == ["ok"]

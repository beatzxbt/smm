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
            messages: Messages to yield.

        Returns:
            None.
        """
        self._messages = list(messages)
        self.closed = False

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
    """Layer 1: WebSocketConnection behaviors."""

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

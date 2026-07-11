"""Focused failure-contract tests for the shared WebSocket connection."""

from __future__ import annotations

import aiohttp
import pytest

from framework.base.stream.connection import WebSocketConnection
from mm_toolbox.logging.standard import Logger


@pytest.mark.asyncio
async def test_disconnected_operations_fail() -> None:
    connection = WebSocketConnection("wss://example", Logger(name="test"))
    with pytest.raises(ConnectionError, match="not connected"):
        await connection.send(b"payload")
    with pytest.raises(ConnectionError, match="not connected"):
        await connection.receive()


@pytest.mark.asyncio
async def test_reconnect_uses_bounded_exponential_backoff(monkeypatch) -> None:
    connection = WebSocketConnection(
        "wss://example",
        Logger(name="test"),
        max_reconnect_attempts=3,
    )
    delays: list[float] = []

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    async def fail_connect() -> None:
        raise ConnectionError("unavailable")

    monkeypatch.setattr("framework.base.stream.connection.asyncio.sleep", record_sleep)
    monkeypatch.setattr(connection, "connect", fail_connect)

    assert await connection._reconnect_with_backoff() is False
    assert delays == [1.0, 2.0, 4.0]


@pytest.mark.asyncio
async def test_reconnect_callback_failure_does_not_block_others() -> None:
    connection = WebSocketConnection("wss://example", Logger(name="test"))
    calls: list[str] = []

    async def fail() -> None:
        raise RuntimeError("boom")

    async def succeed() -> None:
        calls.append("called")

    connection.add_reconnect_callback(fail)
    connection.add_reconnect_callback(succeed)
    await connection._notify_reconnect()

    assert calls == ["called"]


def test_control_frames_are_filtered_and_close_state() -> None:
    connection = WebSocketConnection("wss://example", Logger(name="test"))
    connection._is_connected = True

    closed = aiohttp.WSMessage(aiohttp.WSMsgType.CLOSED, b"", None)
    ping = aiohttp.WSMessage(aiohttp.WSMsgType.PING, b"", None)

    assert connection._normalize_message(closed) is None
    assert connection.is_connected is False
    assert connection._normalize_message(ping) is None

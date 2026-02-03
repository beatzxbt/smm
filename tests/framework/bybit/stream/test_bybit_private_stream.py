"""Tests for framework.bybit.stream.private.BybitPrivateDataStream."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import aiohttp
import msgspec
import pytest

from framework.base.common import Instrument, InstrumentType, Venue
from framework.base.stream.models import AccountMsg, ExecutionMsg, OrderMsg, PositionMsg
from framework.bybit.stream.private import BybitPrivateDataStream
from framework.base.trading.models import Secret
from mm_toolbox.logging.standard import Logger


@dataclass
class FakeWsMessage:
    """Simple websocket message stub.

    Args:
        type: aiohttp websocket message type.
        data: Raw message payload.
    """

    type: aiohttp.WSMsgType
    data: bytes


class FakeWs:
    """Async websocket iterator for Bybit private stream tests.

    Args:
        messages: List of encoded websocket payloads.
    """

    def __init__(self, messages: list[bytes]) -> None:
        self._messages = list(messages)

    async def __aenter__(self):
        """Enter the async context manager.

        Returns:
            FakeWs: Instance for async iteration.
        """
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Exit the async context manager.

        Args:
            exc_type: Exception type, if raised.
            exc: Exception instance, if raised.
            tb: Traceback, if raised.

        Returns:
            bool: False to propagate exceptions.
        """
        return False

    def __aiter__(self):
        """Return async iterator.

        Returns:
            FakeWs: Iterator instance.
        """
        return self

    async def __anext__(self):
        """Return next websocket message.

        Returns:
            FakeWsMessage: Message wrapper with type/data.

        Raises:
            StopAsyncIteration: When messages are exhausted.
        """
        if not self._messages:
            raise StopAsyncIteration
        payload = self._messages.pop(0)
        return FakeWsMessage(type=aiohttp.WSMsgType.TEXT, data=payload)

    async def send_bytes(self, _data: bytes) -> None:
        """No-op send_bytes for subscription messages.

        Args:
            _data: Encoded subscription payload.
        """
        return None


class FakeSession:
    """Async session stub for Bybit private stream tests.

    Args:
        messages: List of encoded websocket payloads.
    """

    def __init__(self, messages: list[bytes]) -> None:
        self._messages = messages

    async def __aenter__(self):
        """Enter the async context manager.

        Returns:
            FakeSession: Session instance.
        """
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Exit the async context manager.

        Args:
            exc_type: Exception type, if raised.
            exc: Exception instance, if raised.
            tb: Traceback, if raised.

        Returns:
            bool: False to propagate exceptions.
        """
        return False

    def ws_connect(self, _url: str):
        """Return a fake websocket connection.

        Args:
            _url: Websocket URL.

        Returns:
            FakeWs: Fake websocket iterator.
        """
        return FakeWs(self._messages)


def make_instrument() -> Instrument:
    """Create a standard Bybit instrument for tests.

    Returns:
        Instrument: BTCUSDT perpetual contract.
    """
    return Instrument(
        venue=Venue.BYBIT,
        symbol="BTCUSDT",
        base="BTC",
        quote="USDT",
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )


class TestBybitPrivateStream:
    """Layer 3: Private stream message handling."""

    @pytest.mark.asyncio
    async def test_stream_order_broadcasts_order_msg(
        self,
        bybit_payloads,
        monkeypatch,
    ) -> None:
        """Test order stream broadcasts OrderMsg.

        Args:
            bybit_payloads: Payload factory namespace fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        messages = [
            msgspec.json.encode(bybit_payloads.make_bybit_private_order_message())
        ]

        async def _auth(self, _ws) -> bool:
            """Bypass authentication for tests.

            Args:
                _ws: Websocket placeholder.

            Returns:
                bool: True for success.
            """
            return True

        monkeypatch.setattr(
            "framework.bybit.stream.private.aiohttp.ClientSession",
            lambda: FakeSession(messages),
        )
        monkeypatch.setattr(BybitPrivateDataStream, "_authenticate_ws", _auth)

        queue = asyncio.Queue()
        stream = BybitPrivateDataStream(
            key=Secret(name="key", value="k"),
            secret=Secret(name="secret", value="s"),
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )
        instruments = [make_instrument()]
        stream._instruments = instruments

        await stream.stream_order(instruments)

        msg = queue.get_nowait()
        assert isinstance(msg, OrderMsg)

    @pytest.mark.asyncio
    async def test_stream_position_broadcasts_position_msg(
        self,
        bybit_payloads,
        monkeypatch,
    ) -> None:
        """Test position stream broadcasts PositionMsg.

        Args:
            bybit_payloads: Payload factory namespace fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        messages = [
            msgspec.json.encode(bybit_payloads.make_bybit_private_position_message())
        ]

        async def _auth(self, _ws) -> bool:
            """Bypass authentication for tests.

            Args:
                _ws: Websocket placeholder.

            Returns:
                bool: True for success.
            """
            return True

        monkeypatch.setattr(
            "framework.bybit.stream.private.aiohttp.ClientSession",
            lambda: FakeSession(messages),
        )
        monkeypatch.setattr(BybitPrivateDataStream, "_authenticate_ws", _auth)

        queue = asyncio.Queue()
        stream = BybitPrivateDataStream(
            key=Secret(name="key", value="k"),
            secret=Secret(name="secret", value="s"),
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )
        instruments = [make_instrument()]
        stream._instruments = instruments

        await stream.stream_position(instruments)

        msg = queue.get_nowait()
        assert isinstance(msg, PositionMsg)

    @pytest.mark.asyncio
    async def test_stream_execution_broadcasts_execution_msg(
        self,
        bybit_payloads,
        monkeypatch,
    ) -> None:
        """Test execution stream broadcasts ExecutionMsg.

        Args:
            bybit_payloads: Payload factory namespace fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        messages = [
            msgspec.json.encode(bybit_payloads.make_bybit_private_execution_message())
        ]

        async def _auth(self, _ws) -> bool:
            """Bypass authentication for tests.

            Args:
                _ws: Websocket placeholder.

            Returns:
                bool: True for success.
            """
            return True

        monkeypatch.setattr(
            "framework.bybit.stream.private.aiohttp.ClientSession",
            lambda: FakeSession(messages),
        )
        monkeypatch.setattr(BybitPrivateDataStream, "_authenticate_ws", _auth)

        queue = asyncio.Queue()
        stream = BybitPrivateDataStream(
            key=Secret(name="key", value="k"),
            secret=Secret(name="secret", value="s"),
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )
        instruments = [make_instrument()]
        stream._instruments = instruments

        await stream.stream_execution(instruments)

        msg = queue.get_nowait()
        assert isinstance(msg, ExecutionMsg)

    @pytest.mark.asyncio
    async def test_stream_account_broadcasts_account_msg(
        self,
        bybit_payloads,
        monkeypatch,
    ) -> None:
        """Test wallet stream broadcasts AccountMsg.

        Args:
            bybit_payloads: Payload factory namespace fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        messages = [
            msgspec.json.encode(bybit_payloads.make_bybit_private_wallet_message())
        ]

        async def _auth(self, _ws) -> bool:
            """Bypass authentication for tests.

            Args:
                _ws: Websocket placeholder.

            Returns:
                bool: True for success.
            """
            return True

        monkeypatch.setattr(
            "framework.bybit.stream.private.aiohttp.ClientSession",
            lambda: FakeSession(messages),
        )
        monkeypatch.setattr(BybitPrivateDataStream, "_authenticate_ws", _auth)

        queue = asyncio.Queue()
        stream = BybitPrivateDataStream(
            key=Secret(name="key", value="k"),
            secret=Secret(name="secret", value="s"),
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )
        instruments = [make_instrument()]
        stream._instruments = instruments

        await stream.stream_account()

        msg = queue.get_nowait()
        assert isinstance(msg, AccountMsg)

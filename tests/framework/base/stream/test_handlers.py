"""
Tests for BaseStreamHandler behavior.

Validates subscription tracking, broadcast flow, and reconnect resubscription.
"""

from __future__ import annotations

import asyncio

import pytest

from framework.base.common import (
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Venue,
)
from framework.base.stream.handlers import TickerStreamHandler
from framework.base.stream.models import (
    DataStreamEvent,
    DataStreamEventMsg,
    Msg,
    StreamType,
)
from mm_toolbox.logging.standard import Logger


class FakeConnection:
    """Stub websocket connection for handler tests."""

    def __init__(self) -> None:
        """Initialize the fake connection.

        Returns:
            None.
        """
        self.sent: list[bytes] = []
        self.connected = False
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._callbacks: list[callable] = []

    async def connect(self) -> None:
        """Mark the connection as established.

        Returns:
            None.
        """
        self.connected = True

    async def disconnect(self) -> None:
        """Mark the connection as closed.

        Returns:
            None.
        """
        self.connected = False
        await self._queue.put(None)

    async def send(self, data: bytes) -> None:
        """Capture outgoing payloads.

        Args:
            data: Serialized payload bytes.

        Returns:
            None.
        """
        self.sent.append(data)

    def add_reconnect_callback(self, callback) -> None:
        """Register reconnect callbacks.

        Args:
            callback: Callback to invoke on reconnect.

        Returns:
            None.
        """
        self._callbacks.append(callback)

    async def trigger_reconnect(self) -> None:
        """Invoke reconnect callbacks.

        Returns:
            None.
        """
        for callback in self._callbacks:
            await callback()

    async def push(self, data: bytes) -> None:
        """Push an incoming message into the queue.

        Args:
            data: Raw websocket payload bytes.

        Returns:
            None.
        """
        await self._queue.put(data)

    async def __aiter__(self):
        """Yield queued websocket payloads.

        Returns:
            AsyncIterator[bytes]: Iterator over queued payloads.
        """
        while True:
            data = await self._queue.get()
            if data is None:
                break
            yield data


class DummyHandler(TickerStreamHandler):
    """Minimal handler for exercising BaseStreamHandler behavior."""

    def __init__(
        self,
        connection: FakeConnection,
        instrument_collection: InstrumentCollection,
        queue: asyncio.Queue[Msg],
    ) -> None:
        """Initialize the dummy handler.

        Args:
            connection: Fake websocket connection.
            instrument_collection: Shared instrument collection.
            queue: Consumer queue for broadcasts.

        Returns:
            None.
        """
        super().__init__(
            connection=connection,
            instrument_collection=instrument_collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )
        self.decode_calls = 0

    def build_authentication_payload(self) -> bytes:
        """No authentication needed for test handler.

        Returns:
            bytes: Empty bytes.
        """
        return b""

    def build_subscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build a dummy subscribe payload.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Ignored for test handler.

        Returns:
            bytes: Serialized payload bytes.
        """
        return b"subscribe"

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Build a dummy unsubscribe payload.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Ignored for test handler.

        Returns:
            bytes: Serialized payload bytes.
        """
        return b"unsubscribe"

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Increment decode count and broadcast a stub message.

        Args:
            raw_msg: Raw websocket payload bytes.

        Returns:
            None.
        """
        self.decode_calls += 1
        self.broadcast(
            DataStreamEventMsg(
                time_ms=0,
                venue=Venue.NULL,
                event=DataStreamEvent.START,
                changes={},
                state={},
                time_next_check_ms=None,
            )
        )


class TestBaseStreamHandler:
    """BaseStreamHandler lifecycle and subscription helpers."""

    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe(self) -> None:
        """Test subscription tracking and payload sending.

        Returns:
            None.
        """
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        handler = DummyHandler(
            connection=connection,
            instrument_collection=InstrumentCollection([instrument]),
            queue=asyncio.Queue(),
        )
        await handler.start()
        await handler.subscribe([instrument])
        assert instrument in handler.get_subscribed_instruments()
        assert connection.sent[-1] == b"subscribe"

        await handler.unsubscribe([instrument])
        assert instrument not in handler.get_subscribed_instruments()
        assert connection.sent[-1] == b"unsubscribe"
        await handler.stop()

    @pytest.mark.asyncio
    async def test_broadcasts_messages(self) -> None:
        """Test broadcast forwards messages to consumer queues.

        Returns:
            None.
        """
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base="ETH",
            quote="USDT",
            symbol="ETHUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        queue: asyncio.Queue[Msg] = asyncio.Queue()
        handler = DummyHandler(
            connection=connection,
            instrument_collection=InstrumentCollection([instrument]),
            queue=queue,
        )
        handler.broadcast(
            DataStreamEventMsg(
                time_ms=0,
                venue=Venue.NULL,
                event=DataStreamEvent.START,
                changes={},
                state={},
                time_next_check_ms=None,
            )
        )
        assert not queue.empty()

    @pytest.mark.asyncio
    async def test_message_loop_decodes(self) -> None:
        """Test that incoming messages trigger decode calls.

        Returns:
            None.
        """
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        queue: asyncio.Queue[Msg] = asyncio.Queue()
        handler = DummyHandler(
            connection=connection,
            instrument_collection=InstrumentCollection([instrument]),
            queue=queue,
        )
        await handler.start()
        await connection.push(b"payload")
        await asyncio.sleep(0)
        assert handler.decode_calls == 1
        await handler.stop()

    @pytest.mark.asyncio
    async def test_resubscribe_on_reconnect(self) -> None:
        """Test reconnect triggers resubscribe payloads.

        Returns:
            None.
        """
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=3,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        handler = DummyHandler(
            connection=connection,
            instrument_collection=InstrumentCollection([instrument]),
            queue=asyncio.Queue(),
        )
        await handler.start()
        await handler.subscribe([instrument])
        await connection.trigger_reconnect()
        assert connection.sent[-1] == b"subscribe"
        await handler.stop()

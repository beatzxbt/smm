"""
Tests for BaseStreamHandler behavior.

Validates subscription tracking, broadcast flow, and reconnect resubscription.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable

import pytest

from framework.base.common import (
    Asset,
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Symbol,
    Venue,
)
from framework.base.stream.handlers import SubscriptionTransport, TickerStreamHandler
from framework.base.stream.shared import StreamSharedContext
from framework.base.stream.models import (
    DataStreamEvent,
    DataStreamEventMsg,
    StreamType,
)
from framework.base.tools import SimpleCache
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer
from mm_toolbox.time import time_ns


class FakeConnection:
    """Stub websocket connection for handler tests."""

    def __init__(self) -> None:
        """Initialize the fake connection."""
        self.sent: list[bytes] = []
        self.connected = False
        self.url = "wss://example/ws"
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.url_updates: list[str] = []
        self._queue = GenericRingBuffer(64)
        self._callbacks: list[Callable[[], Awaitable[None]]] = []

    async def connect(self) -> None:
        """Mark the connection as established."""
        if self.connected:
            return
        self.connect_calls += 1
        self.connected = True

    async def disconnect(self) -> None:
        """Mark the connection as closed."""
        if not self.connected:
            return
        self.disconnect_calls += 1
        self.connected = False
        self._queue.insert(None)

    async def send(self, data: bytes) -> None:
        """Capture outgoing payloads.

        Args:
            data: Serialized payload bytes.

        Raises:
            ConnectionError: If the websocket is not connected.
        """
        if not self.connected:
            raise ConnectionError("WebSocket is not connected.")
        self.sent.append(data)

    def add_reconnect_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Register reconnect callbacks.

        Args:
            callback: Callback to invoke on reconnect.

        """
        self._callbacks.append(callback)

    def set_url(self, url: str) -> None:
        """Update the websocket URL.

        Args:
            url: New websocket URL.

        Raises:
            ValueError: If the URL is empty.
        """
        if not url:
            raise ValueError("Invalid url; expected non-empty string.")
        self.url = url
        self.url_updates.append(url)

    async def trigger_reconnect(self) -> None:
        """Invoke reconnect callbacks."""
        if not self.connected:
            return
        for callback in self._callbacks:
            await callback()

    async def push(self, data: bytes) -> None:
        """Push an incoming message into the queue.

        Args:
            data: Raw websocket payload bytes.

        Raises:
            ConnectionError: If the websocket is not connected.
        """
        if not self.connected:
            raise ConnectionError("WebSocket is not connected.")
        self._queue.insert((time_ns(), data))

    async def __aiter__(self) -> AsyncIterator[tuple[int, bytes]]:
        """Yield queued websocket payloads.

        Returns:
            AsyncIterator[tuple[int, bytes]]: Iterator over receive timestamp and
            queued payload bytes.
        """
        while True:
            data = await self._queue.aconsume()
            if data is None:
                break
            yield data


class DummyHandler(TickerStreamHandler):
    """Minimal handler for exercising BaseStreamHandler behavior."""

    def __init__(
        self,
        connection: FakeConnection,
        instrument_collection: InstrumentCollection,
        queue: GenericRingBuffer,
    ) -> None:
        """Initialize the dummy handler.

        Args:
            connection: Fake websocket connection.
            instrument_collection: Shared instrument collection.
            queue: Consumer ring buffer for broadcasts.

        """
        super().__init__(
            connection=connection,
            instrument_collection=instrument_collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
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

    async def decode_and_broadcast(
        self,
        recv_time_ns: int,
        raw_msg: bytes,
    ) -> None:
        """Increment decode count and broadcast a stub message.

        Args:
            raw_msg: Raw websocket payload bytes.
            recv_time_ns: Receive timestamp captured when the websocket payload
                arrived.

        """
        del raw_msg, recv_time_ns
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


class UrlQueryDummyHandler(TickerStreamHandler):
    """Ticker handler using URL-query style subscriptions."""

    subscription_transport = SubscriptionTransport.URL_QUERY

    def __init__(
        self,
        connection: FakeConnection,
        instrument_collection: InstrumentCollection,
        queue: GenericRingBuffer,
    ) -> None:
        """Initialize the URL-query dummy handler.

        Args:
            connection: Fake websocket connection.
            instrument_collection: Shared instrument collection.
            queue: Consumer ring buffer for broadcasts.
        """
        super().__init__(
            connection=connection,
            instrument_collection=instrument_collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )

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
        """Return payload bytes when called unexpectedly.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Optional stream types.

        Returns:
            bytes: Placeholder payload bytes.
        """
        return b"unexpected-subscribe"

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Return payload bytes when called unexpectedly.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Optional stream types.

        Returns:
            bytes: Placeholder payload bytes.
        """
        return b"unexpected-unsubscribe"

    def build_subscription_url(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> str | None:
        """Build a URL with symbol streams encoded in the query.

        Args:
            instruments: Active instrument subscriptions.
            stream_types: Optional stream types (unused).

        Returns:
            str | None: URL for active subscriptions, else None.
        """
        del stream_types
        if not instruments:
            return None
        streams = "&".join(f"{inst.symbol.lower()}@aggTrade" for inst in instruments)
        return f"wss://example/ws/stream?{streams}"

    async def decode_and_broadcast(
        self,
        recv_time_ns: int,
        raw_msg: bytes,
    ) -> None:
        """No-op decoder for test handler.

        Args:
            raw_msg: Raw websocket payload bytes.
            recv_time_ns: Receive timestamp captured when the websocket payload
                arrived.
        """
        del raw_msg, recv_time_ns


class MissingUrlBuilderDummyHandler(UrlQueryDummyHandler):
    """URL-query handler that intentionally delegates URL construction to base."""

    def build_subscription_url(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> str | None:
        """Delegate URL construction to the base implementation.

        Args:
            instruments: Active instrument subscriptions.
            stream_types: Optional stream types.

        Returns:
            str | None: URL for active subscriptions, else None.
        """
        return TickerStreamHandler.build_subscription_url(
            self,
            instruments=instruments,
            stream_types=stream_types,
        )


class SharedContextDummyHandler(TickerStreamHandler):
    """Ticker handler exposing manager-scoped shared cache for tests."""

    shared_slots = {"test.seq_cache": SimpleCache}

    def __init__(
        self,
        connection: FakeConnection,
        instrument_collection: InstrumentCollection,
        queue: GenericRingBuffer,
        shared_context: StreamSharedContext | None = None,
    ) -> None:
        """Initialize shared-context test handler.

        Args:
            connection: Fake websocket connection.
            instrument_collection: Shared instrument collection.
            queue: Consumer ring buffer for broadcasts.
            shared_context: Optional manager-scoped shared context.
        """
        super().__init__(
            connection=connection,
            instrument_collection=instrument_collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            shared_context=shared_context,
        )
        self.seq_cache: SimpleCache = self.get_shared("test.seq_cache", SimpleCache)

    def build_authentication_payload(self) -> bytes:
        """Return an empty auth payload for tests.

        Returns:
            bytes: Empty payload bytes.
        """
        return b""

    def build_subscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Return a fixed subscribe payload for tests.

        Args:
            instruments: Instruments to subscribe to.
            stream_types: Optional stream types.

        Returns:
            bytes: Serialized payload bytes.
        """
        del instruments, stream_types
        return b"subscribe"

    def build_unsubscribe_payload(
        self,
        instruments: list[Instrument],
        stream_types: set[StreamType] | None = None,
    ) -> bytes:
        """Return a fixed unsubscribe payload for tests.

        Args:
            instruments: Instruments to unsubscribe from.
            stream_types: Optional stream types.

        Returns:
            bytes: Serialized payload bytes.
        """
        del instruments, stream_types
        return b"unsubscribe"

    async def decode_and_broadcast(
        self,
        recv_time_ns: int,
        raw_msg: bytes,
    ) -> None:
        """No-op decoder for shared-context tests.

        Args:
            raw_msg: Raw websocket payload bytes.
            recv_time_ns: Receive timestamp captured when the websocket payload
                arrived.
        """
        del raw_msg, recv_time_ns


class TestBaseStreamHandler:
    """BaseStreamHandler lifecycle and subscription helpers."""

    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe(self) -> None:
        """Test subscription tracking and payload sending."""
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        handler = DummyHandler(
            connection=connection,
            instrument_collection=InstrumentCollection([instrument]),
            queue=GenericRingBuffer(1),
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
        """Test broadcast forwards messages to the consumer ring buffer."""
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDT"),
            symbol=Symbol("ETHUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        queue = GenericRingBuffer(16)
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
        assert not queue.is_empty()

    @pytest.mark.asyncio
    async def test_message_loop_decodes(self) -> None:
        """Test that incoming messages trigger decode calls."""
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        queue = GenericRingBuffer(16)
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
        """Test reconnect triggers resubscribe payloads."""
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=3,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        handler = DummyHandler(
            connection=connection,
            instrument_collection=InstrumentCollection([instrument]),
            queue=GenericRingBuffer(1),
        )
        await handler.start()
        await handler.subscribe([instrument])
        await connection.trigger_reconnect()
        assert connection.sent[-1] == b"subscribe"
        await handler.stop()

    @pytest.mark.asyncio
    async def test_url_query_mode_delays_connect_until_subscription(self) -> None:
        """Test URL mode starts idle and connects after first subscription."""
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=4,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        handler = UrlQueryDummyHandler(
            connection=connection,
            instrument_collection=InstrumentCollection([instrument]),
            queue=GenericRingBuffer(1),
        )

        await handler.start()
        assert connection.connect_calls == 0

        await handler.subscribe([instrument])
        assert connection.connect_calls == 1
        assert connection.url_updates == ["wss://example/ws/stream?btcusdt@aggTrade"]
        assert connection.sent == []
        await handler.stop()

    @pytest.mark.asyncio
    async def test_url_query_mode_rotates_url_on_subscription_change(self) -> None:
        """Test URL mode reconnects when subscription composition changes."""
        connection = FakeConnection()
        btc = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=5,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        eth = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDT"),
            symbol=Symbol("ETHUSDT"),
            code=6,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        handler = UrlQueryDummyHandler(
            connection=connection,
            instrument_collection=InstrumentCollection([btc, eth]),
            queue=GenericRingBuffer(1),
        )

        await handler.start()
        await handler.subscribe([btc])
        await handler.subscribe([eth])

        assert connection.connect_calls == 2
        assert connection.disconnect_calls == 1
        assert connection.url_updates == [
            "wss://example/ws/stream?btcusdt@aggTrade",
            "wss://example/ws/stream?btcusdt@aggTrade&ethusdt@aggTrade",
        ]
        assert connection.sent == []
        await handler.stop()

    @pytest.mark.asyncio
    async def test_url_query_mode_disconnects_when_empty(self) -> None:
        """Test URL mode disconnects when the last instrument is removed."""
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=7,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        handler = UrlQueryDummyHandler(
            connection=connection,
            instrument_collection=InstrumentCollection([instrument]),
            queue=GenericRingBuffer(1),
        )

        await handler.start()
        await handler.subscribe([instrument])
        await handler.unsubscribe([instrument])

        assert connection.connected is False
        assert connection.disconnect_calls == 1
        assert connection.sent == []
        await handler.stop()

    @pytest.mark.asyncio
    async def test_url_query_mode_raises_if_url_builder_not_overridden(self) -> None:
        """Test URL mode fails fast when URL builder is not implemented."""
        connection = FakeConnection()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=17,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        handler = MissingUrlBuilderDummyHandler(
            connection=connection,
            instrument_collection=InstrumentCollection([instrument]),
            queue=GenericRingBuffer(1),
        )

        await handler.start()
        with pytest.raises(NotImplementedError, match="build_subscription_url"):
            await handler.subscribe([instrument])
        await handler.stop()

    def test_shared_context_isolated_by_default(self) -> None:
        """Test handlers use separate shared objects when no context is passed."""
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=8,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        collection = InstrumentCollection([instrument])

        handler_a = SharedContextDummyHandler(
            connection=FakeConnection(),
            instrument_collection=collection,
            queue=GenericRingBuffer(1),
        )
        handler_b = SharedContextDummyHandler(
            connection=FakeConnection(),
            instrument_collection=collection,
            queue=GenericRingBuffer(1),
        )
        assert handler_a.seq_cache is not handler_b.seq_cache

    def test_shared_context_reused_when_provided(self) -> None:
        """Test handlers reuse the same shared object with a shared context."""
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=9,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        collection = InstrumentCollection([instrument])
        shared_context = StreamSharedContext()

        handler_a = SharedContextDummyHandler(
            connection=FakeConnection(),
            instrument_collection=collection,
            queue=GenericRingBuffer(1),
            shared_context=shared_context,
        )
        handler_b = SharedContextDummyHandler(
            connection=FakeConnection(),
            instrument_collection=collection,
            queue=GenericRingBuffer(1),
            shared_context=shared_context,
        )

        assert handler_a.seq_cache is handler_b.seq_cache
        assert "test.seq_cache" in shared_context.values

"""
Tests for stream managers.

Covers lifecycle broadcasting, subscription tracking, and end-to-end flow.
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
from framework.base.schema import MessageId, Moments
from framework.base.stream.handlers import TickerStreamHandler
from framework.base.stream.manager import MarketStreamManager
from framework.base.stream.models import (
    DataStreamEvent,
    DataStreamEventMsg,
    MarketDataStreamType,
    StreamType,
    TickerMsg,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer
from mm_toolbox.time import time_ns


class NoopHandler:
    """No-op handler stub for manager tests."""

    def __init__(self) -> None:
        """Initialize the handler stub."""
        self.start_calls = 0
        self.stop_calls = 0
        self.subscribe_calls = 0
        self.unsubscribe_calls = 0

    async def start(self) -> None:
        """Record a start call."""
        self.start_calls += 1

    async def stop(self) -> None:
        """Record a stop call."""
        self.stop_calls += 1

    async def subscribe(self, _instruments: list[Instrument]) -> None:
        """Record a subscribe call.

        Args:
            _instruments: Instruments to subscribe to.

        """
        self.subscribe_calls += 1

    async def unsubscribe(self, _instruments: list[Instrument]) -> None:
        """Record an unsubscribe call.

        Args:
            _instruments: Instruments to unsubscribe from.

        """
        self.unsubscribe_calls += 1


class PushConnection:
    """Stub connection that yields injected messages."""

    def __init__(self) -> None:
        """Initialize the push connection."""
        self.connected = False
        self._queue = GenericRingBuffer(64)
        self._callbacks: list[Callable[[], Awaitable[None]]] = []

    async def connect(self) -> None:
        """Mark the connection as established."""
        if self.connected:
            return
        self.connected = True

    async def disconnect(self) -> None:
        """Stop message iteration."""
        if not self.connected:
            return
        self.connected = False
        self._queue.insert(None)

    async def send(self, _data: bytes) -> None:
        """No-op send.

        Args:
            _data: Serialized payload bytes.

        Raises:
            ConnectionError: If the websocket is not connected.
        """
        if not self.connected:
            raise ConnectionError("WebSocket is not connected.")
        return None

    def add_reconnect_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Register reconnect callbacks.

        Args:
            callback: Callback to invoke on reconnect.

        """
        self._callbacks.append(callback)

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


class SimpleTickerHandler(TickerStreamHandler):
    """Ticker handler that emits a fixed TickerMsg."""

    def __init__(
        self,
        connection: PushConnection,
        instrument_collection: InstrumentCollection,
        queue: GenericRingBuffer,
        instrument: Instrument,
    ) -> None:
        """Initialize the simple ticker handler.

        Args:
            connection: Push connection for messages.
            instrument_collection: Shared instrument collection.
            queue: Consumer ring buffer for broadcasts.
            instrument: Instrument to emit.

        """
        super().__init__(
            connection=connection,
            instrument_collection=instrument_collection,
            venue=instrument.venue,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )
        self._instrument = instrument

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
        """Broadcast a deterministic ticker message.

        Args:
            raw_msg: Raw websocket payload bytes.
            recv_time_ns: Receive timestamp captured when the websocket payload
                arrived.

        """
        del raw_msg
        msg_id = MessageId(recv_time_ns=recv_time_ns)
        msg = TickerMsg(
            id=msg_id,
            origin_id=msg_id,
            moments=Moments(
                exch_time_ns=time_ns(),
                recv_time_ns=recv_time_ns,
            ),
            instrument=self._instrument,
            is_snapshot=False,
            mark_price=1.0,
            index_price=1.0,
            funding_rate=0.0,
            funding_period_min=480,
            next_funding_time_ms=0.0,
            open_interest=0.0,
            avg_volume_24h=0.0,
            price_chg_24h_pct=0.0,
        )
        self.broadcast(msg)


class DummyMarketManager(MarketStreamManager):
    """MarketStreamManager stub for tests."""

    @classmethod
    async def create(
        cls,
        exchange,
        logger,
        consumer_buffer,
    ) -> "DummyMarketManager":
        """Create a dummy manager.

        Args:
            exchange: Exchange client stub.
            logger: Logger instance.
            consumer_buffer: Ring buffer to broadcast messages to.

        Returns:
            DummyMarketManager: Manager instance for tests.
        """
        raise NotImplementedError("Use direct initialization in tests.")


class TestMarketStreamManagerLifecycle:
    """MarketStreamManager lifecycle and state tracking."""

    @pytest.mark.asyncio
    async def test_start_stop_broadcasts_events(self, monkeypatch) -> None:
        """Test START/STOP lifecycle events are broadcast.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        """
        queue = GenericRingBuffer(16)
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
        instrument_collection = InstrumentCollection([instrument])
        handler = NoopHandler()
        manager = DummyMarketManager(
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            instrument_collection=instrument_collection,
            ticker_handler=handler,
            bbo_handler=handler,
            orderbook_handler=handler,
            trades_handler=handler,
        )

        async def _fast_heartbeat(*_args, **_kwargs) -> None:
            """No-op heartbeat for test isolation.

            Args:
                _args: Positional args (unused).
                _kwargs: Keyword args (unused).

            """
            return None

        monkeypatch.setattr(manager, "_heartbeat_loop", _fast_heartbeat)
        await manager.start()
        start_msg = queue.consume()
        assert isinstance(start_msg, DataStreamEventMsg)
        assert start_msg.event == DataStreamEvent.START

        await manager.stop()
        stop_msg = queue.consume()
        assert isinstance(stop_msg, DataStreamEventMsg)
        assert stop_msg.event == DataStreamEvent.STOP

    @pytest.mark.asyncio
    async def test_subscription_state_tracking(self, monkeypatch) -> None:
        """Test subscription state helpers update correctly.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        """
        queue = GenericRingBuffer(16)
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
        instrument_collection = InstrumentCollection([instrument])
        handler = NoopHandler()
        manager = DummyMarketManager(
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            instrument_collection=instrument_collection,
            ticker_handler=handler,
            bbo_handler=handler,
            orderbook_handler=handler,
            trades_handler=handler,
        )

        async def _fast_heartbeat(*_args, **_kwargs) -> None:
            """No-op heartbeat for test isolation.

            Args:
                _args: Positional args (unused).
                _kwargs: Keyword args (unused).

            """
            return None

        monkeypatch.setattr(manager, "_heartbeat_loop", _fast_heartbeat)
        await manager.start()
        await manager.subscribe([instrument], {MarketDataStreamType.TICKER})
        assert manager.is_subscribed(instrument, MarketDataStreamType.TICKER)
        await manager.unsubscribe([instrument], {MarketDataStreamType.TICKER})
        assert not manager.is_subscribed(instrument, MarketDataStreamType.TICKER)
        await manager.stop()


class TestMarketStreamManagerLazyHandlerLifecycle:
    """MarketStreamManager lazy start/stop behavior for handlers."""

    @pytest.mark.asyncio
    async def test_handlers_start_and_stop_only_when_subscribed(
        self, monkeypatch
    ) -> None:
        """Test handlers only run for active subscribed stream types.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
        """
        queue = GenericRingBuffer(16)
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
        instrument_collection = InstrumentCollection([instrument])
        ticker_handler = NoopHandler()
        bbo_handler = NoopHandler()
        orderbook_handler = NoopHandler()
        trades_handler = NoopHandler()
        manager = DummyMarketManager(
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            instrument_collection=instrument_collection,
            ticker_handler=ticker_handler,
            bbo_handler=bbo_handler,
            orderbook_handler=orderbook_handler,
            trades_handler=trades_handler,
        )

        async def _fast_heartbeat(*_args, **_kwargs) -> None:
            """No-op heartbeat for test isolation.

            Args:
                _args: Positional args (unused).
                _kwargs: Keyword args (unused).
            """
            return None

        monkeypatch.setattr(manager, "_heartbeat_loop", _fast_heartbeat)
        await manager.start()
        assert ticker_handler.start_calls == 0
        assert bbo_handler.start_calls == 0
        assert orderbook_handler.start_calls == 0
        assert trades_handler.start_calls == 0

        await manager.subscribe([instrument], {MarketDataStreamType.TICKER})
        assert ticker_handler.start_calls == 1
        assert ticker_handler.subscribe_calls == 1
        assert bbo_handler.start_calls == 0
        assert orderbook_handler.start_calls == 0
        assert trades_handler.start_calls == 0

        await manager.unsubscribe([instrument], {MarketDataStreamType.TICKER})
        assert ticker_handler.unsubscribe_calls == 1
        assert ticker_handler.stop_calls == 1
        assert bbo_handler.stop_calls == 0
        assert orderbook_handler.stop_calls == 0
        assert trades_handler.stop_calls == 0

        await manager.stop()
        assert ticker_handler.stop_calls == 1

    @pytest.mark.asyncio
    async def test_duplicate_subscribe_unsubscribe_are_noops(self, monkeypatch) -> None:
        """Test duplicate requests do not trigger extra handler calls.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
        """
        queue = GenericRingBuffer(16)
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDT"),
            symbol=Symbol("ETHUSDT"),
            code=8,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        instrument_collection = InstrumentCollection([instrument])
        ticker_handler = NoopHandler()
        manager = DummyMarketManager(
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            instrument_collection=instrument_collection,
            ticker_handler=ticker_handler,
            bbo_handler=NoopHandler(),
            orderbook_handler=NoopHandler(),
            trades_handler=NoopHandler(),
        )

        async def _fast_heartbeat(*_args, **_kwargs) -> None:
            """No-op heartbeat for test isolation.

            Args:
                _args: Positional args (unused).
                _kwargs: Keyword args (unused).
            """
            return None

        monkeypatch.setattr(manager, "_heartbeat_loop", _fast_heartbeat)
        await manager.start()

        await manager.subscribe([instrument], {MarketDataStreamType.TICKER})
        await manager.subscribe([instrument], {MarketDataStreamType.TICKER})
        assert ticker_handler.start_calls == 1
        assert ticker_handler.subscribe_calls == 1

        await manager.unsubscribe([instrument], {MarketDataStreamType.TICKER})
        await manager.unsubscribe([instrument], {MarketDataStreamType.TICKER})
        assert ticker_handler.unsubscribe_calls == 1
        assert ticker_handler.stop_calls == 1

        await manager.stop()


class TestMessageFlowEndToEnd:
    """End-to-end message flow from handler to consumer ring buffer."""

    @pytest.mark.asyncio
    async def test_message_flow(self, monkeypatch) -> None:
        """Test handler messages reach the consumer ring buffer.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        """
        queue = GenericRingBuffer(16)
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
        instrument_collection = InstrumentCollection([instrument])
        connection = PushConnection()
        ticker_handler = SimpleTickerHandler(
            connection=connection,
            instrument_collection=instrument_collection,
            queue=queue,
            instrument=instrument,
        )
        manager = DummyMarketManager(
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            instrument_collection=instrument_collection,
            ticker_handler=ticker_handler,
            bbo_handler=NoopHandler(),
            orderbook_handler=NoopHandler(),
            trades_handler=NoopHandler(),
        )

        async def _fast_heartbeat(*_args, **_kwargs) -> None:
            """No-op heartbeat for test isolation.

            Args:
                _args: Positional args (unused).
                _kwargs: Keyword args (unused).

            """
            return None

        monkeypatch.setattr(manager, "_heartbeat_loop", _fast_heartbeat)
        await manager.start()
        await manager.subscribe([instrument], {MarketDataStreamType.TICKER})
        await connection.push(b"payload")
        await asyncio.sleep(0)
        received = queue.consume_all()
        assert any(isinstance(item, TickerMsg) for item in received)
        await manager.stop()

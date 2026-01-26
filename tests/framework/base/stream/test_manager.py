"""
Tests for stream managers.

Covers lifecycle broadcasting, subscription tracking, and end-to-end flow.
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
from framework.base.stream.manager import MarketStreamManager
from framework.base.stream.models import (
    DataStreamEvent,
    DataStreamEventMsg,
    MarketDataStreamType,
    Moments,
    Msg,
    StreamType,
    TickerMsg,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.time import time_ns


class NoopHandler:
    """No-op handler stub for manager tests."""

    def __init__(self) -> None:
        """Initialize the handler stub.

        Returns:
            None.
        """
        self.start_calls = 0
        self.stop_calls = 0
        self.subscribe_calls = 0
        self.unsubscribe_calls = 0

    async def start(self) -> None:
        """Record a start call.

        Returns:
            None.
        """
        self.start_calls += 1

    async def stop(self) -> None:
        """Record a stop call.

        Returns:
            None.
        """
        self.stop_calls += 1

    async def subscribe(self, _instruments: list[Instrument]) -> None:
        """Record a subscribe call.

        Args:
            _instruments: Instruments to subscribe to.

        Returns:
            None.
        """
        self.subscribe_calls += 1

    async def unsubscribe(self, _instruments: list[Instrument]) -> None:
        """Record an unsubscribe call.

        Args:
            _instruments: Instruments to unsubscribe from.

        Returns:
            None.
        """
        self.unsubscribe_calls += 1


class PushConnection:
    """Stub connection that yields injected messages."""

    def __init__(self) -> None:
        """Initialize the push connection.

        Returns:
            None.
        """
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._callbacks: list[callable] = []

    async def connect(self) -> None:
        """No-op connect.

        Returns:
            None.
        """
        return None

    async def disconnect(self) -> None:
        """Stop message iteration.

        Returns:
            None.
        """
        await self._queue.put(None)

    async def send(self, _data: bytes) -> None:
        """No-op send.

        Args:
            _data: Serialized payload bytes.

        Returns:
            None.
        """
        return None

    def add_reconnect_callback(self, callback) -> None:
        """Register reconnect callbacks.

        Args:
            callback: Callback to invoke on reconnect.

        Returns:
            None.
        """
        self._callbacks.append(callback)

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


class SimpleTickerHandler(TickerStreamHandler):
    """Ticker handler that emits a fixed TickerMsg."""

    def __init__(
        self,
        connection: PushConnection,
        instrument_collection: InstrumentCollection,
        queue: asyncio.Queue[Msg],
        instrument: Instrument,
    ) -> None:
        """Initialize the simple ticker handler.

        Args:
            connection: Push connection for messages.
            instrument_collection: Shared instrument collection.
            queue: Consumer queue for broadcasts.
            instrument: Instrument to emit.

        Returns:
            None.
        """
        super().__init__(
            connection=connection,
            instrument_collection=instrument_collection,
            venue=instrument.venue,
            logger=Logger(name="test"),
            consumer_queues=[queue],
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

    async def decode_and_broadcast(self, raw_msg: bytes) -> None:
        """Broadcast a deterministic ticker message.

        Args:
            raw_msg: Raw websocket payload bytes.

        Returns:
            None.
        """
        msg = TickerMsg(
            moments=Moments(
                exch_time_ns=time_ns(),
                recv_time_ns=time_ns(),
            ),
            venue=self._instrument.venue,
            instrument=self._instrument,
            mark_price=1.0,
            index_price=1.0,
            funding_rate=0.0,
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
        consumer_queues,
    ) -> "DummyMarketManager":
        """Create a dummy manager.

        Args:
            exchange: Exchange client stub.
            logger: Logger instance.
            consumer_queues: Queues to broadcast messages to.

        Returns:
            DummyMarketManager: Manager instance for tests.
        """
        raise NotImplementedError("Use direct initialization in tests.")


class TestMarketStreamManagerLifecycle:
    """Layer 3: MarketStreamManager lifecycle and state tracking."""

    @pytest.mark.asyncio
    async def test_start_stop_broadcasts_events(self, monkeypatch) -> None:
        """Test START/STOP lifecycle events are broadcast.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        queue: asyncio.Queue[Msg] = asyncio.Queue()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
        )
        instrument_collection = InstrumentCollection([instrument])
        handler = NoopHandler()
        manager = DummyMarketManager(
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_queues=[queue],
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

            Returns:
                None.
            """
            return None

        monkeypatch.setattr(manager, "_heartbeat_loop", _fast_heartbeat)
        await manager.start()
        start_msg = queue.get_nowait()
        assert isinstance(start_msg, DataStreamEventMsg)
        assert start_msg.event == DataStreamEvent.START

        await manager.stop()
        stop_msg = queue.get_nowait()
        assert isinstance(stop_msg, DataStreamEventMsg)
        assert stop_msg.event == DataStreamEvent.STOP

    @pytest.mark.asyncio
    async def test_subscription_state_tracking(self, monkeypatch) -> None:
        """Test subscription state helpers update correctly.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        queue: asyncio.Queue[Msg] = asyncio.Queue()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base="ETH",
            quote="USDT",
            symbol="ETHUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        instrument_collection = InstrumentCollection([instrument])
        handler = NoopHandler()
        manager = DummyMarketManager(
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_queues=[queue],
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

            Returns:
                None.
            """
            return None

        monkeypatch.setattr(manager, "_heartbeat_loop", _fast_heartbeat)
        await manager.start()
        await manager.subscribe([instrument], {MarketDataStreamType.TICKER})
        assert manager.is_subscribed(instrument, MarketDataStreamType.TICKER)
        await manager.unsubscribe([instrument], {MarketDataStreamType.TICKER})
        assert not manager.is_subscribed(instrument, MarketDataStreamType.TICKER)
        await manager.stop()


class TestMessageFlowEndToEnd:
    """Layer 3: End-to-end message flow from handler to consumer queue."""

    @pytest.mark.asyncio
    async def test_message_flow(self, monkeypatch) -> None:
        """Test handler messages reach consumer queues.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.

        Returns:
            None.
        """
        queue: asyncio.Queue[Msg] = asyncio.Queue()
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
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
            consumer_queues=[queue],
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

            Returns:
                None.
            """
            return None

        monkeypatch.setattr(manager, "_heartbeat_loop", _fast_heartbeat)
        await manager.start()
        await manager.subscribe([instrument], {MarketDataStreamType.TICKER})
        await connection.push(b"payload")
        await asyncio.sleep(0)
        received = [queue.get_nowait() for _ in range(queue.qsize())]
        assert any(isinstance(item, TickerMsg) for item in received)
        await manager.stop()

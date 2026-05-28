"""
Tests for Binance stream handlers.

Validates ticker polling cadence and orderbook decoding behavior.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import msgspec
import pytest

from framework.base.common import (
    Asset,
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Symbol,
    Venue,
)
from framework.base.stream.shared import StreamSharedContext
from framework.base.stream.models import OrderbookMsg
from framework.binance.stream.handlers import (
    BinanceBBOHandler,
    BinanceOrderbookHandler,
    BinanceTickerHandler,
    BinanceTradesHandler,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer


class DummyConnection:
    """Connection stub for handler tests."""

    def __init__(self) -> None:
        """Initialize the dummy connection."""
        self.sent: list[bytes] = []
        self.connected = False
        self.url = "wss://example/ws"
        self._callbacks: list[Callable[[], Awaitable[None]]] = []

    async def connect(self) -> None:
        """Mark the connection as established."""
        if self.connected:
            return
        self.connected = True

    async def disconnect(self) -> None:
        """Mark the connection as closed."""
        if not self.connected:
            return
        self.connected = False

    async def send(self, data: bytes) -> None:
        """Capture outbound payloads.

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


class FakeResponse:
    """Minimal response stub."""

    def __init__(self, data) -> None:
        """Initialize the response.

        Args:
            data: Response payload data.
        """
        self.is_successful = True
        self.data = data
        self.err_msg = ""


class FakeTicker:
    """Minimal ticker response stub."""

    def __init__(self, instrument: Instrument) -> None:
        """Initialize the ticker response.

        Args:
            instrument: Instrument associated with the response.
        """
        self.instrument = instrument
        self.price_chg_24h = 0.1
        self.avg_volume_24h = 10.0


class FakeExchange:
    """Exchange stub for polling tests."""

    async def get_open_interest(self, instruments: list[Instrument]) -> FakeResponse:
        """Return a fake open interest response.

        Args:
            instruments: Instruments to request.

        Returns:
            FakeResponse: Response containing open interest values.
        """
        return FakeResponse([1.0 for _ in instruments])

    async def get_ticker(self, instruments: list[Instrument]) -> FakeResponse:
        """Return a fake ticker response.

        Args:
            instruments: Instruments to request.

        Returns:
            FakeResponse: Response containing ticker stats.
        """
        return FakeResponse([FakeTicker(inst) for inst in instruments])


def make_collection() -> InstrumentCollection:
    """Create a Binance instrument collection fixture.

    Returns:
        InstrumentCollection: Collection containing a Binance instrument.
    """
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
    return InstrumentCollection([instrument])


class TestBinanceTickerHandler:
    """Layer 2: Binance ticker handler behavior."""

    @pytest.mark.asyncio
    async def test_poll_interval_is_one_second(self, monkeypatch) -> None:
        """Test ticker polling uses 1-second interval.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
        """
        delays: list[float] = []
        original_sleep = asyncio.sleep

        async def _fake_sleep(delay: float) -> None:
            """Capture sleep delay and cancel loop.

            Args:
                delay: Sleep delay in seconds.
            """
            if delay in {1.0, 2.0, 5.0, 10.0}:
                delays.append(delay)
                raise asyncio.CancelledError
            await original_sleep(0)

        monkeypatch.setattr(
            "framework.binance.stream.handlers.asyncio.sleep", _fake_sleep
        )

        collection = make_collection()
        instrument = collection.instruments[0]
        handler = BinanceTickerHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=GenericRingBuffer(1),
            exchange=FakeExchange(),  # type: ignore[arg-type]
        )
        handler._is_running = True
        handler._subscribed_instruments.add(instrument)
        task = asyncio.create_task(handler._poll_ticker())
        await asyncio.gather(task, return_exceptions=True)
        assert 1.0 in delays


class TestBinanceOrderbookHandler:
    """Layer 2: Binance orderbook handler behavior."""

    @pytest.mark.asyncio
    async def test_orderbook_decoding(self) -> None:
        """Test depth updates decode to orderbook messages."""
        queue = GenericRingBuffer(16)
        collection = make_collection()
        handler = BinanceOrderbookHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )
        payload = {
            "e": "depthUpdate",
            "E": 1,
            "T": 1,
            "s": "BTCUSDT",
            "U": 1,
            "u": 2,
            "pu": 0,
            "b": [["30000.0", "1.0"]],
            "a": [["30001.0", "2.0"]],
        }
        await handler.decode_and_broadcast(1, msgspec.json.encode(payload))
        msg = queue.consume()
        assert isinstance(msg, OrderbookMsg)
        assert msg.is_bbo is False


class TestBinanceTradesHandler:
    """Layer 2: Binance trades handler behavior."""

    @pytest.mark.asyncio
    async def test_drops_insurance_fund_trades_with_debug(self, monkeypatch) -> None:
        """Test insurance fund trades are logged at debug and dropped.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
        """
        queue = GenericRingBuffer(16)
        collection = make_collection()
        logger = Logger(name="test")
        debug_calls: list[str] = []

        def _debug(message: str) -> None:
            """Capture debug logs.

            Args:
                message: Debug log message.
            """
            debug_calls.append(message)

        monkeypatch.setattr(logger, "debug", _debug)

        handler = BinanceTradesHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=logger,
            consumer_buffer=queue,
        )
        payload = {
            "e": "trade",
            "E": 1,
            "T": 1,
            "s": "BTCUSDT",
            "t": 10,
            "p": "0",
            "q": "0",
            "X": "INSURANCE_FUND",
            "m": True,
        }
        await handler.decode_and_broadcast(1, msgspec.json.encode(payload))
        assert queue.is_empty()
        assert len(debug_calls) == 1
        assert "INSURANCE_FUND" in debug_calls[0]


class TestBinanceRequestIds:
    """Layer 2: Binance request id sequencing behavior."""

    def test_request_ids_are_scoped_per_handler(self) -> None:
        """Test each handler has an independent request-id counter."""
        queue = GenericRingBuffer(16)
        collection = make_collection()
        instrument = collection.instruments[0]

        ticker_handler = BinanceTickerHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            exchange=FakeExchange(),  # type: ignore[arg-type]
        )
        orderbook_handler = BinanceOrderbookHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )

        ticker_subscribe_1 = msgspec.json.decode(
            ticker_handler.build_subscribe_payload([instrument])
        )
        ticker_subscribe_2 = msgspec.json.decode(
            ticker_handler.build_subscribe_payload([instrument])
        )
        orderbook_subscribe_1 = msgspec.json.decode(
            orderbook_handler.build_subscribe_payload([instrument])
        )

        assert ticker_subscribe_1["id"] == 1
        assert ticker_subscribe_2["id"] == 2
        assert orderbook_subscribe_1["id"] == 1


class TestBinanceSharedContext:
    """Layer 2: shared-context behavior across Binance handlers."""

    @pytest.mark.asyncio
    async def test_orderbook_cache_shared_across_handlers(self) -> None:
        """Test BBO and orderbook handlers share sequence cache with one context."""
        queue = GenericRingBuffer(16)
        collection = make_collection()
        shared_context = StreamSharedContext()

        bbo_handler = BinanceBBOHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            shared_context=shared_context,
        )
        orderbook_handler = BinanceOrderbookHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            shared_context=shared_context,
        )

        assert (
            bbo_handler._orderbook_seq_id_cache
            is orderbook_handler._orderbook_seq_id_cache
        )

    @pytest.mark.asyncio
    async def test_cross_handler_dedup_uses_shared_sequence_cache(self) -> None:
        """Test duplicate sequence ids are dropped across BBO/orderbook handlers."""
        queue = GenericRingBuffer(16)
        collection = make_collection()
        shared_context = StreamSharedContext()

        bbo_handler = BinanceBBOHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            shared_context=shared_context,
        )
        orderbook_handler = BinanceOrderbookHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_buffer=queue,
            shared_context=shared_context,
        )

        bbo_payload = {
            "u": 10,
            "E": 1,
            "T": 1,
            "s": "BTCUSDT",
            "b": "30000.0",
            "B": "1.0",
            "a": "30001.0",
            "A": "2.0",
        }
        orderbook_payload = {
            "e": "depthUpdate",
            "E": 2,
            "T": 2,
            "s": "BTCUSDT",
            "U": 10,
            "u": 10,
            "pu": 9,
            "b": [["30000.0", "1.0"]],
            "a": [["30001.0", "2.0"]],
        }

        await bbo_handler.decode_and_broadcast(
            1,
            msgspec.json.encode(bbo_payload),
        )
        msg = queue.consume()
        assert isinstance(msg, OrderbookMsg)
        assert msg.is_bbo is True

        await orderbook_handler.decode_and_broadcast(
            1,
            msgspec.json.encode(orderbook_payload),
        )
        assert queue.is_empty()

"""
Tests for Binance stream handlers.

Validates ticker polling cadence and orderbook decoding behavior.
"""

from __future__ import annotations

import asyncio

import msgspec
import pytest

from framework.base.common import (
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Venue,
)
from framework.base.stream.models import OrderbookMsg
from framework.binance.stream.handlers import (
    BinanceOrderbookHandler,
    BinanceTickerHandler,
    BinanceTradesHandler,
)
from mm_toolbox.logging.standard import Logger


class DummyConnection:
    """Connection stub for handler tests."""

    def __init__(self) -> None:
        """Initialize the dummy connection."""
        self.sent: list[bytes] = []
        self._callbacks: list[callable] = []

    async def connect(self) -> None:
        """No-op connect."""
        return None

    async def disconnect(self) -> None:
        """No-op disconnect."""
        return None

    async def send(self, data: bytes) -> None:
        """Capture outbound payloads.

        Args:
            data: Serialized payload bytes.
        """
        self.sent.append(data)

    def add_reconnect_callback(self, callback) -> None:
        """Register reconnect callbacks.

        Args:
            callback: Callback to invoke on reconnect.
        """
        self._callbacks.append(callback)


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
        base="BTC",
        quote="USDT",
        symbol="BTCUSDT",
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

        async def _fake_sleep(delay: float) -> None:
            """Capture sleep delay and cancel loop.

            Args:
                delay: Sleep delay in seconds.
            """
            delays.append(delay)
            raise asyncio.CancelledError

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
            consumer_queues=[],
            exchange=FakeExchange(),  # type: ignore[arg-type]
        )
        handler._is_running = True
        handler._subscribed_instruments.add(instrument)
        task = asyncio.create_task(handler._poll_ticker_stats())
        await asyncio.gather(task, return_exceptions=True)
        assert 1.0 in delays


class TestBinanceOrderbookHandler:
    """Layer 2: Binance orderbook handler behavior."""

    @pytest.mark.asyncio
    async def test_orderbook_decoding(self) -> None:
        """Test depth updates decode to orderbook messages."""
        queue: asyncio.Queue = asyncio.Queue()
        collection = make_collection()
        handler = BinanceOrderbookHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=Logger(name="test"),
            consumer_queues=[queue],
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
        await handler.decode_and_broadcast(msgspec.json.encode(payload))
        msg = queue.get_nowait()
        assert isinstance(msg, OrderbookMsg)
        assert msg.is_bbo is False


class TestBinanceTradesHandler:
    """Layer 2: Binance trades handler behavior."""

    @pytest.mark.asyncio
    async def test_drops_insurance_fund_trades_with_trace(self, monkeypatch) -> None:
        """Test insurance fund trades are logged at trace and dropped.

        Args:
            monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
        """
        queue: asyncio.Queue = asyncio.Queue()
        collection = make_collection()
        logger = Logger(name="test")
        trace_calls: list[str] = []

        def _trace(message: str) -> None:
            """Capture trace logs.

            Args:
                message: Trace log message.
            """
            trace_calls.append(message)

        monkeypatch.setattr(logger, "trace", _trace)

        handler = BinanceTradesHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BINANCE_USDM,
            logger=logger,
            consumer_queues=[queue],
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
        await handler.decode_and_broadcast(msgspec.json.encode(payload))
        assert queue.empty()
        assert len(trace_calls) == 1
        assert "INSURANCE_FUND" in trace_calls[0]

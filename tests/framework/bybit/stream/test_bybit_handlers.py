"""
Tests for Bybit stream handlers.

Validates typed decoding, partial cache behavior, and deduplication logic.
"""

from __future__ import annotations

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
from framework.base.stream.models import OrderbookMsg, TickerMsg, TradeMsg
from framework.bybit.stream.handlers import (
    BybitBBOHandler,
    BybitOrderbookHandler,
    BybitTickerHandler,
    BybitTradesHandler,
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


def make_instrument_collection() -> InstrumentCollection:
    """Create a Bybit instrument collection fixture.

    Returns:
        InstrumentCollection: Collection containing a Bybit instrument.
    """
    instrument = Instrument(
        venue=Venue.BYBIT,
        base=Asset("BTC"),
        quote=Asset("USDT"),
        symbol=Symbol("BTCUSDT"),
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )
    return InstrumentCollection([instrument])


class TestBybitTickerHandler:
    """Layer 2: Bybit ticker handler behavior."""

    @pytest.mark.asyncio
    async def test_partial_cache_uses_previous_values(self) -> None:
        """Test delta updates merge with cached values."""
        queue = GenericRingBuffer(16)
        handler = BybitTickerHandler(
            connection=DummyConnection(),
            instrument_collection=make_instrument_collection(),
            venue=Venue.BYBIT,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )

        snapshot_payload = {
            "topic": "tickers.BTCUSDT",
            "type": "snapshot",
            "data": {
                "symbol": "BTCUSDT",
                "tickDirection": "PlusTick",
                "price24hPcnt": 0.01,
                "lastPrice": 30000.0,
                "prevPrice24h": 29900.0,
                "highPrice24h": 31000.0,
                "lowPrice24h": 29000.0,
                "prevPrice1h": 29500.0,
                "markPrice": 30000.0,
                "indexPrice": 29950.0,
                "openInterest": 10.0,
                "openInterestValue": 100.0,
                "turnover24h": 200.0,
                "volume24h": 50.0,
                "nextFundingTime": 1700000000000,
                "fundingRate": 0.0001,
            },
        }
        delta_payload = {
            "topic": "tickers.BTCUSDT",
            "type": "delta",
            "data": {
                "symbol": "BTCUSDT",
                "tickDirection": "PlusTick",
                "price24hPcnt": 0.0,
                "lastPrice": 0.0,
                "prevPrice24h": 0.0,
                "highPrice24h": 0.0,
                "lowPrice24h": 0.0,
                "prevPrice1h": 0.0,
                "markPrice": 0.0,
                "indexPrice": 0.0,
                "openInterest": 0.0,
                "openInterestValue": 0.0,
                "turnover24h": 0.0,
                "volume24h": 0.0,
                "nextFundingTime": 0,
                "fundingRate": 0.0,
            },
        }

        await handler.decode_and_broadcast(
            1,
            msgspec.json.encode(snapshot_payload),
        )
        await handler.decode_and_broadcast(
            1,
            msgspec.json.encode(delta_payload),
        )

        last_msg = None
        while not queue.is_empty():
            last_msg = queue.consume()
        assert isinstance(last_msg, TickerMsg)
        assert last_msg.mark_price == pytest.approx(30000.0)
        assert last_msg.index_price == pytest.approx(29950.0)


class TestBybitOrderbookHandlers:
    """Layer 2: Bybit orderbook handler behavior."""

    @pytest.mark.asyncio
    async def test_bbo_and_orderbook_flags(self) -> None:
        """Test BBO and orderbook handlers set is_bbo correctly."""
        queue = GenericRingBuffer(16)
        collection = make_instrument_collection()
        bbo_handler = BybitBBOHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BYBIT,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )
        orderbook_handler = BybitOrderbookHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BYBIT,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )
        payload = {
            "topic": "orderbook.1.BTCUSDT",
            "type": "snapshot",
            "data": {
                "s": "BTCUSDT",
                "b": [{"price": 30000.0, "size": 1.0}],
                "a": [{"price": 30001.0, "size": 2.0}],
                "u": 1,
                "seq": 2,
            },
        }
        await bbo_handler.decode_and_broadcast(
            1,
            msgspec.json.encode(payload),
        )
        bbo_msg = queue.consume()
        assert isinstance(bbo_msg, OrderbookMsg)
        assert bbo_msg.is_bbo is True

        await orderbook_handler.decode_and_broadcast(
            1,
            msgspec.json.encode(payload),
        )
        ob_msg = queue.consume()
        assert isinstance(ob_msg, OrderbookMsg)
        assert ob_msg.is_bbo is False


class TestBybitTradesHandler:
    """Layer 2: Bybit trades handler behavior."""

    @pytest.mark.asyncio
    async def test_deduplicates_by_sequence(self) -> None:
        """Test duplicate trades are ignored."""
        queue = GenericRingBuffer(16)
        handler = BybitTradesHandler(
            connection=DummyConnection(),
            instrument_collection=make_instrument_collection(),
            venue=Venue.BYBIT,
            logger=Logger(name="test"),
            consumer_buffer=queue,
        )
        payload = {
            "topic": "publicTrade.BTCUSDT",
            "type": "snapshot",
            "ts": 1700000000000,
            "data": [
                {
                    "T": 1700000000000,
                    "S": "BTCUSDT",
                    "s": "Buy",
                    "v": 1.0,
                    "p": 30000.0,
                    "i": "trade_1",
                    "seq": 1,
                }
            ],
        }
        encoded = msgspec.json.encode(payload)
        await handler.decode_and_broadcast(1, encoded)
        await handler.decode_and_broadcast(1, encoded)

        received = queue.consume_all()
        assert len([msg for msg in received if isinstance(msg, TradeMsg)]) == 1

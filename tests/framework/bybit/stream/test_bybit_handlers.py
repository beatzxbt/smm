"""
Tests for Bybit stream handlers.

Validates typed decoding, partial cache behavior, and deduplication logic.
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
from framework.base.stream.models import OrderbookMsg, TickerMsg, TradeMsg
from framework.bybit.stream.handlers import (
    BybitBBOHandler,
    BybitOrderbookHandler,
    BybitTickerHandler,
    BybitTradesHandler,
)
from mm_toolbox.logging.standard import Logger


class DummyConnection:
    """Connection stub for handler tests."""

    def __init__(self) -> None:
        """Initialize the dummy connection.
        """
        self.sent: list[bytes] = []
        self._callbacks: list[callable] = []

    async def connect(self) -> None:
        """No-op connect.
        """
        return None

    async def disconnect(self) -> None:
        """No-op disconnect.
        """
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


def make_instrument_collection() -> InstrumentCollection:
    """Create a Bybit instrument collection fixture.

    Returns:
        InstrumentCollection: Collection containing a Bybit instrument.
    """
    instrument = Instrument(
        venue=Venue.BYBIT,
        base="BTC",
        quote="USDT",
        symbol="BTCUSDT",
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
    )
    return InstrumentCollection([instrument])


class TestBybitTickerHandler:
    """Layer 2: Bybit ticker handler behavior."""

    @pytest.mark.asyncio
    async def test_partial_cache_uses_previous_values(self) -> None:
        """Test delta updates merge with cached values.
        """
        queue: asyncio.Queue = asyncio.Queue()
        handler = BybitTickerHandler(
            connection=DummyConnection(),
            instrument_collection=make_instrument_collection(),
            venue=Venue.BYBIT,
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )

        snapshot_payload = {
            "topic": "tickers.BTCUSDT",
            "type": "snapshot",
            "data": {
                "symbol": "BTCUSDT",
                "tickDirection": "PlusTick",
                "price24HPcnt": 0.01,
                "lastPrice": 30000.0,
                "prevPrice24H": 29900.0,
                "highPrice24H": 31000.0,
                "lowPrice24H": 29000.0,
                "prevPrice1H": 29500.0,
                "markPrice": 30000.0,
                "indexPrice": 29950.0,
                "openInterest": 10.0,
                "openInterestValue": 100.0,
                "turnover24H": 200.0,
                "volume24H": 50.0,
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
                "price24HPcnt": 0.0,
                "lastPrice": 0.0,
                "prevPrice24H": 0.0,
                "highPrice24H": 0.0,
                "lowPrice24H": 0.0,
                "prevPrice1H": 0.0,
                "markPrice": 0.0,
                "indexPrice": 0.0,
                "openInterest": 0.0,
                "openInterestValue": 0.0,
                "turnover24H": 0.0,
                "volume24H": 0.0,
                "nextFundingTime": 0,
                "fundingRate": 0.0,
            },
        }

        await handler.decode_and_broadcast(msgspec.json.encode(snapshot_payload))
        await handler.decode_and_broadcast(msgspec.json.encode(delta_payload))

        last_msg = None
        while not queue.empty():
            last_msg = queue.get_nowait()
        assert isinstance(last_msg, TickerMsg)
        assert last_msg.mark_price == pytest.approx(30000.0)
        assert last_msg.index_price == pytest.approx(29950.0)


class TestBybitOrderbookHandlers:
    """Layer 2: Bybit orderbook handler behavior."""

    @pytest.mark.asyncio
    async def test_bbo_and_orderbook_flags(self) -> None:
        """Test BBO and orderbook handlers set is_bbo correctly.
        """
        queue: asyncio.Queue = asyncio.Queue()
        collection = make_instrument_collection()
        bbo_handler = BybitBBOHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BYBIT,
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )
        orderbook_handler = BybitOrderbookHandler(
            connection=DummyConnection(),
            instrument_collection=collection,
            venue=Venue.BYBIT,
            logger=Logger(name="test"),
            consumer_queues=[queue],
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
        await bbo_handler.decode_and_broadcast(msgspec.json.encode(payload))
        bbo_msg = queue.get_nowait()
        assert isinstance(bbo_msg, OrderbookMsg)
        assert bbo_msg.is_bbo is True

        await orderbook_handler.decode_and_broadcast(msgspec.json.encode(payload))
        ob_msg = queue.get_nowait()
        assert isinstance(ob_msg, OrderbookMsg)
        assert ob_msg.is_bbo is False


class TestBybitTradesHandler:
    """Layer 2: Bybit trades handler behavior."""

    @pytest.mark.asyncio
    async def test_deduplicates_by_sequence(self) -> None:
        """Test duplicate trades are ignored.
        """
        queue: asyncio.Queue = asyncio.Queue()
        handler = BybitTradesHandler(
            connection=DummyConnection(),
            instrument_collection=make_instrument_collection(),
            venue=Venue.BYBIT,
            logger=Logger(name="test"),
            consumer_queues=[queue],
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
        await handler.decode_and_broadcast(encoded)
        await handler.decode_and_broadcast(encoded)

        received = [queue.get_nowait() for _ in range(queue.qsize())]
        assert len([msg for msg in received if isinstance(msg, TradeMsg)]) == 1

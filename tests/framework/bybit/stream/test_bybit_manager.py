"""
Tests for Bybit stream managers.

Validates manager factories and handler wiring.
"""

from __future__ import annotations

import asyncio

from framework.base.common import (
    Asset,
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Symbol,
    Venue,
)
from framework.bybit.stream.handlers import (
    BybitBBOHandler,
    BybitOrderbookHandler,
    BybitPrivateHandler,
    BybitTickerHandler,
    BybitTradesHandler,
)
from framework.bybit.stream.manager import (
    BybitMarketStreamManager,
    BybitPrivateStreamManager,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer


class FakeHttpClient:
    """Minimal HTTP client stub with credentials."""

    def __init__(self, key: str, secret: str) -> None:
        """Initialize the stub.

        Args:
            key: API key.
            secret: API secret.
        """
        self.key = key
        self.secret = secret


class FakeBybitExchange:
    """Minimal Bybit exchange stub for manager tests."""

    def __init__(self, instruments: InstrumentCollection) -> None:
        """Initialize the exchange stub.

        Args:
            instruments: Instrument collection to return.
        """
        self.venue = Venue.BYBIT
        self.http_client = FakeHttpClient("key", "secret")
        self._instruments = instruments

    async def get_instrument_collection_cached(self) -> InstrumentCollection:
        """Return the cached instrument collection.

        Returns:
            InstrumentCollection: Cached instrument collection.
        """
        return self._instruments


def make_collection() -> InstrumentCollection:
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


class TestBybitMarketStreamManager:
    """Layer 2: Bybit market manager factory behavior."""

    def test_create_builds_handlers(self) -> None:
        """Test manager create wires all handlers."""
        exchange = FakeBybitExchange(make_collection())
        manager = asyncio.run(
            BybitMarketStreamManager.create(
                exchange=exchange,
                logger=Logger(name="test"),
                consumer_buffer=GenericRingBuffer(1),
            )
        )
        assert isinstance(manager._ticker_handler, BybitTickerHandler)
        assert isinstance(manager._bbo_handler, BybitBBOHandler)
        assert isinstance(manager._orderbook_handler, BybitOrderbookHandler)
        assert isinstance(manager._trades_handler, BybitTradesHandler)


class TestBybitPrivateStreamManager:
    """Layer 2: Bybit private manager factory behavior."""

    def test_create_builds_handler(self) -> None:
        """Test private manager wires its unified authenticated handler."""
        exchange = FakeBybitExchange(make_collection())
        manager = asyncio.run(
            BybitPrivateStreamManager.create(
                exchange=exchange,
                logger=Logger(name="test"),
                consumer_buffer=GenericRingBuffer(1),
            )
        )
        assert isinstance(manager._handler, BybitPrivateHandler)

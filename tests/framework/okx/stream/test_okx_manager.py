"""
Tests for OKX stream managers.

Validates factory wiring, handler creation, and credential extraction.
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
from framework.okx.stream.handlers import (
    OkxBBOHandler,
    OkxOrderbookHandler,
    OkxPrivateHandler,
    OkxTickerHandler,
    OkxTradesHandler,
)
from framework.okx.stream.manager import (
    OkxMarketStreamManager,
    OkxPrivateStreamManager,
)
from mm_toolbox.logging.standard import Logger


class FakeOkxHttpClient:
    """OkxHttpClient stub for manager tests."""

    def __init__(self) -> None:
        """Initialize the HTTP client stub."""
        self.key = "test_api_key"
        self.secret = "test_api_secret"
        self.passphrase = "test_passphrase"


class FakeOkxExchange:
    """OkxExchange stub for manager tests."""

    def __init__(self, instruments: InstrumentCollection) -> None:
        """Initialize the exchange stub.

        Args:
            instruments: Instrument collection to return.
        """
        self.venue = Venue.OKX
        self._instruments = instruments
        self.http_client = FakeOkxHttpClient()

    async def get_instrument_collection_cached(
        self, refresh: bool = False
    ) -> InstrumentCollection:
        """Return the cached instrument collection.

        Args:
            refresh: Whether to refresh the collection (ignored in stub).

        Returns:
            InstrumentCollection: Cached instrument collection.
        """
        return self._instruments


def make_collection() -> InstrumentCollection:
    """Create an OKX instrument collection fixture.

    Returns:
        InstrumentCollection: Collection containing an OKX instrument.
    """
    instrument = Instrument(
        venue=Venue.OKX,
        base="BTC",
        quote="USDT",
        symbol="BTC-USDT-SWAP",
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )
    return InstrumentCollection([instrument])


class TestOkxMarketStreamManager:
    """Layer 2: OKX market manager factory behavior."""

    def test_create_builds_handlers(self) -> None:
        """Test manager create wires all handlers."""
        exchange = FakeOkxExchange(make_collection())
        manager = asyncio.run(
            OkxMarketStreamManager.create(
                exchange=exchange,  # type: ignore[arg-type]
                logger=Logger(name="test"),
                consumer_queues=[asyncio.Queue()],
            )
        )
        assert isinstance(manager._ticker_handler, OkxTickerHandler)
        assert isinstance(manager._bbo_handler, OkxBBOHandler)
        assert isinstance(manager._orderbook_handler, OkxOrderbookHandler)
        assert isinstance(manager._trades_handler, OkxTradesHandler)

    def test_create_with_wrong_venue_raises(self) -> None:
        """Test manager create raises for non-OKX exchange."""

        class WrongExchange:
            venue = Venue.BINANCE_USDM

        with pytest.raises(ValueError, match="requires OkxExchange"):
            asyncio.run(
                OkxMarketStreamManager.create(
                    exchange=WrongExchange(),  # type: ignore[arg-type]
                    logger=Logger(name="test"),
                    consumer_queues=[asyncio.Queue()],
                )
            )

    def test_handlers_have_separate_connections(self) -> None:
        """Test each handler has its own connection."""
        exchange = FakeOkxExchange(make_collection())
        manager = asyncio.run(
            OkxMarketStreamManager.create(
                exchange=exchange,  # type: ignore[arg-type]
                logger=Logger(name="test"),
                consumer_queues=[asyncio.Queue()],
            )
        )
        connections = [
            id(manager._ticker_handler._connection),
            id(manager._bbo_handler._connection),
            id(manager._orderbook_handler._connection),
            id(manager._trades_handler._connection),
        ]
        assert len(set(connections)) == 4


class TestOkxPrivateStreamManager:
    """Layer 2: OKX private manager factory behavior."""

    def test_create_builds_handler(self) -> None:
        """Test manager create wires private handler."""
        exchange = FakeOkxExchange(make_collection())
        manager = asyncio.run(
            OkxPrivateStreamManager.create(
                exchange=exchange,  # type: ignore[arg-type]
                logger=Logger(name="test"),
                consumer_queues=[asyncio.Queue()],
            )
        )
        assert isinstance(manager._handler, OkxPrivateHandler)

    def test_create_extracts_credentials(self) -> None:
        """Test manager extracts credentials from http client."""
        exchange = FakeOkxExchange(make_collection())
        manager = asyncio.run(
            OkxPrivateStreamManager.create(
                exchange=exchange,  # type: ignore[arg-type]
                logger=Logger(name="test"),
                consumer_queues=[asyncio.Queue()],
            )
        )
        handler: OkxPrivateHandler = manager._handler  # type: ignore[assignment]
        assert handler._api_key == "test_api_key"
        assert handler._api_secret == "test_api_secret"
        assert handler._passphrase == "test_passphrase"

    def test_create_with_wrong_venue_raises(self) -> None:
        """Test manager create raises for non-OKX exchange."""

        class WrongExchange:
            venue = Venue.BINANCE_USDM

        with pytest.raises(ValueError, match="requires OkxExchange"):
            asyncio.run(
                OkxPrivateStreamManager.create(
                    exchange=WrongExchange(),  # type: ignore[arg-type]
                    logger=Logger(name="test"),
                    consumer_queues=[asyncio.Queue()],
                )
            )

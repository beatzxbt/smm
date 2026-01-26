"""
Tests for Binance stream managers.

Validates factory wiring and stream type resolution for private streams.
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
from framework.base.stream.models import PrivateDataStreamType
from framework.binance.stream.handlers import (
    BinanceBBOHandler,
    BinanceOrderbookHandler,
    BinanceTickerHandler,
    BinanceTradesHandler,
)
from framework.binance.stream.manager import (
    BinanceMarketStreamManager,
    BinancePrivateStreamManager,
)
from framework.binance.stream.models import (
    AccountUpdateData,
    AccountUpdateStreamUpdate,
    OrderUpdateOrderData,
    OrderUpdateStreamUpdate,
)
from framework.binance.trading.exchange import BinanceExchange
from mm_toolbox.logging.standard import Logger


class FakeResponse:
    """Minimal response stub."""

    def __init__(self, data: str) -> None:
        """Initialize the response.

        Args:
            data: Listen key data.
        """
        self.is_successful = True
        self.data = data
        self.err_msg = ""


class FakeBinanceExchange(BinanceExchange):
    """BinanceExchange stub for manager tests."""

    def __init__(self, instruments: InstrumentCollection) -> None:
        """Initialize the exchange stub.

        Args:
            instruments: Instrument collection to return.
        """
        self.venue = Venue.BINANCE_USDM
        self._instruments = instruments

    async def get_instrument_collection_cached(self) -> InstrumentCollection:
        """Return the cached instrument collection.

        Returns:
            InstrumentCollection: Cached instrument collection.
        """
        return self._instruments

    async def get_listen_key(self) -> FakeResponse:
        """Return a fake listen key response.

        Returns:
            FakeResponse: Fake listen key response.
        """
        return FakeResponse("listen_key")


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
    )
    return InstrumentCollection([instrument])


class TestBinanceMarketStreamManager:
    """Layer 2: Binance market manager factory behavior."""

    def test_create_builds_handlers(self) -> None:
        """Test manager create wires all handlers.
        """
        exchange = FakeBinanceExchange(make_collection())
        manager = asyncio.run(
            BinanceMarketStreamManager.create(
                exchange=exchange,
                logger=Logger(name="test"),
                consumer_queues=[asyncio.Queue()],
            )
        )
        assert isinstance(manager._ticker_handler, BinanceTickerHandler)
        assert isinstance(manager._bbo_handler, BinanceBBOHandler)
        assert isinstance(manager._orderbook_handler, BinanceOrderbookHandler)
        assert isinstance(manager._trades_handler, BinanceTradesHandler)


class TestBinancePrivateStreamManager:
    """Layer 2: Binance private manager stream resolution."""

    @pytest.mark.skip(reason="_resolve_stream_types not implemented for Binance")
    def test_resolves_stream_types(self) -> None:
        """Test private manager resolves stream types from payloads.
        """
        exchange = FakeBinanceExchange(make_collection())
        manager = asyncio.run(
            BinancePrivateStreamManager.create(
                exchange=exchange,
                logger=Logger(name="test"),
                consumer_queues=[asyncio.Queue()],
            )
        )
        order_payload = OrderUpdateStreamUpdate(
            event_time=1,
            transaction_time=1,
            order=OrderUpdateOrderData(
                symbol="BTCUSDT",
                side="BUY",
                client_order_id="client_1",
                order_type="LIMIT",
                time_in_force="GTC",
                quantity="1.0",
                price="30000",
                avg_price="30000",
                last_exec_qty="0",
                cum_exec_qty="0",
                last_exec_price="0",
                commission="0",
                commission_asset="USDT",
                trade_time=1,
                create_time=1,
                is_maker=False,
                order_id=1,
                position_side="LONG",
                status="NEW",
                reduce_only=False,
            ),
        )
        account_payload = AccountUpdateStreamUpdate(
            event_time=1,
            transaction_time=1,
            account_data=AccountUpdateData(
                balances=[],
                positions=[],
                maintenance_margin="0",
                maintenance_margin_level="0",
                unrealized_pnl="0",
                unrealized_pnl_usd="0",
            ),
        )
        assert manager._resolve_stream_types(order_payload) == {
            PrivateDataStreamType.ORDER,
            PrivateDataStreamType.EXECUTION,
        }
        assert manager._resolve_stream_types(account_payload) == {
            PrivateDataStreamType.POSITION,
            PrivateDataStreamType.ACCOUNT,
        }

"""tests.framework.binance.stream.test_binance_market_stream"""

from __future__ import annotations

import asyncio

import msgspec
import pytest

from framework.base.stream.models import OrderbookMsg, TickerMsg, TradeMsg
from framework.binance.stream.market import BinanceMarketDataStream
from framework.binance.stream.structs import (
    BookTickerStreamUpdate,
    DiffBookDepthStreamUpdate,
    MarkPriceStreamUpdate,
    OpenInterestInfo,
    TickerStats24h,
    TradeStreamUpdate,
)
from mm_toolbox.logging.standard import Logger


def make_fake_ws_single(messages: list[bytes]):
    """Create a WsSingle test double for queued messages.

    Args:
        messages: Encoded websocket payloads to yield.

    Returns:
        type: WsSingle-compatible class.
    """

    class FakeWsSingle:
        """Async iterable yielding preset websocket messages."""

        def __init__(self, _config) -> None:
            """Initialize the fake websocket.

            Args:
                _config: Websocket configuration (unused).
            """
            self._messages = list(messages)

        async def __aenter__(self):
            """Enter the async context.

            Returns:
                FakeWsSingle: Self instance.
            """
            return self

        async def __aexit__(self, exc_type, exc, tb):
            """Exit the async context.

            Args:
                exc_type: Exception type, if raised.
                exc: Exception instance, if raised.
                tb: Traceback, if raised.

            Returns:
                bool: False to propagate exceptions.
            """
            return False

        def __aiter__(self):
            """Return async iterator.

            Returns:
                FakeWsSingle: Iterator instance.
            """
            return self

        async def __anext__(self):
            """Return the next websocket message.

            Returns:
                bytes: Encoded websocket payload.

            Raises:
                StopAsyncIteration: When messages are exhausted.
            """
            if not self._messages:
                raise StopAsyncIteration
            return self._messages.pop(0)

    return FakeWsSingle


class TestBinanceMarketDataStream:
    """Layer 3: Binance market stream message routing."""

    @pytest.mark.asyncio
    async def test_stream_ticker_broadcasts_message(
        self,
        binance_instrument,
        monkeypatch,
    ) -> None:
        """Test mark price stream emits ticker messages.

        Args:
            binance_instrument: Binance instrument fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        queue = asyncio.Queue()
        stream = BinanceMarketDataStream(
            logger=Logger(name="test"),
            consumer_queues=[queue],
            is_usd_margined=True,
        )
        stream._instruments = [binance_instrument]

        async def _noop_update(self, instruments) -> None:
            """No-op updater for cached stats in tests.

            Args:
                instruments: Instruments to update (unused).
            """
            return None

        monkeypatch.setattr(
            BinanceMarketDataStream,
            "_update_open_interest_map",
            _noop_update,
        )
        monkeypatch.setattr(
            BinanceMarketDataStream,
            "_update_ticker_stats_24h_map",
            _noop_update,
        )

        stream.instrument_to_open_interest_map[binance_instrument] = OpenInterestInfo(
            open_interest=123.0
        )
        stream.instrument_to_ticker_stats_24h_map[binance_instrument] = TickerStats24h(
            price_chg_24h_pct=1.5,
            avg_volume_24h=200.0,
        )

        payload = MarkPriceStreamUpdate(
            event_time=1234,
            symbol="BTCUSDT",
            mark_price="30000.0",
            index_price="29990.0",
            estimated_settle_price="0",
            funding_rate="0.0001",
            next_funding_time=1234567890,
        )
        encoded = msgspec.json.encode(payload)

        monkeypatch.setattr(
            "framework.binance.stream.market.WsSingle",
            make_fake_ws_single([encoded]),
        )

        await stream.stream_ticker([binance_instrument])

        assert not queue.empty()
        msg = queue.get_nowait()
        assert isinstance(msg, TickerMsg)
        assert msg.instrument.symbol == "BTCUSDT"
        assert msg.open_interest == pytest.approx(123.0)
        assert msg.avg_volume_24h == pytest.approx(200.0)
        assert msg.price_chg_24h_pct == pytest.approx(1.5)

    @pytest.mark.asyncio
    async def test_stream_top_of_orderbook_broadcasts_message(
        self,
        binance_instrument,
        monkeypatch,
    ) -> None:
        """Test book ticker stream emits BBO messages.

        Args:
            binance_instrument: Binance instrument fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        queue = asyncio.Queue()
        stream = BinanceMarketDataStream(
            logger=Logger(name="test"),
            consumer_queues=[queue],
            is_usd_margined=True,
        )
        stream._instruments = [binance_instrument]

        payload = BookTickerStreamUpdate(
            update_id=1,
            event_time=2,
            transaction_time=3,
            symbol="BTCUSDT",
            best_bid_price="30000.0",
            best_bid_qty="1.0",
            best_ask_price="30001.0",
            best_ask_qty="2.0",
        )
        encoded = msgspec.json.encode(payload)

        monkeypatch.setattr(
            "framework.binance.stream.market.WsSingle",
            make_fake_ws_single([encoded]),
        )

        await stream.stream_top_of_orderbook([binance_instrument])

        assert not queue.empty()
        msg = queue.get_nowait()
        assert isinstance(msg, OrderbookMsg)
        assert msg.is_bbo is True
        assert msg.bids[0].price == pytest.approx(30000.0)

    @pytest.mark.asyncio
    async def test_stream_full_orderbook_broadcasts_message(
        self,
        binance_instrument,
        monkeypatch,
    ) -> None:
        """Test depth stream emits full orderbook messages.

        Args:
            binance_instrument: Binance instrument fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        queue = asyncio.Queue()
        stream = BinanceMarketDataStream(
            logger=Logger(name="test"),
            consumer_queues=[queue],
            is_usd_margined=True,
        )
        stream._instruments = [binance_instrument]

        payload = DiffBookDepthStreamUpdate(
            event_type="depthUpdate",
            event_time=2,
            transaction_time=3,
            symbol="BTCUSDT",
            first_update_id=1,
            final_update_id=2,
            prev_final_update_id=0,
            bids=[("30000.0", "1.0")],
            asks=[("30001.0", "2.0")],
        )
        encoded = msgspec.json.encode(payload)

        monkeypatch.setattr(
            "framework.binance.stream.market.WsSingle",
            make_fake_ws_single([encoded]),
        )

        await stream.stream_full_orderbook([binance_instrument])

        assert not queue.empty()
        msg = queue.get_nowait()
        assert isinstance(msg, OrderbookMsg)
        assert msg.is_bbo is False
        assert msg.asks[0].price == pytest.approx(30001.0)

    @pytest.mark.asyncio
    async def test_stream_trades_dedupes_by_trade_id(
        self,
        binance_instrument,
        monkeypatch,
    ) -> None:
        """Test trade stream ignores duplicate trade IDs.

        Args:
            binance_instrument: Binance instrument fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        queue = asyncio.Queue()
        stream = BinanceMarketDataStream(
            logger=Logger(name="test"),
            consumer_queues=[queue],
            is_usd_margined=True,
        )
        stream._instruments = [binance_instrument]

        trade_update = TradeStreamUpdate(
            event_time=2,
            transaction_time=3,
            symbol="BTCUSDT",
            trade_id=10,
            price="30000.0",
            quantity="0.1",
            is_buyer_maker=False,
        )
        encoded_messages = [
            msgspec.json.encode(trade_update),
            msgspec.json.encode(trade_update),
        ]

        monkeypatch.setattr(
            "framework.binance.stream.market.WsSingle",
            make_fake_ws_single(encoded_messages),
        )

        await stream.stream_trades([binance_instrument])

        messages = []
        while not queue.empty():
            messages.append(queue.get_nowait())

        assert len(messages) == 1
        msg = messages[0]
        assert isinstance(msg, TradeMsg)
        assert msg.trades[0].is_buy is True

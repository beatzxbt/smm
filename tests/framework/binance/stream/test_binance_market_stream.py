"""tests.framework.binance.stream.test_binance_market_stream"""

from __future__ import annotations


import msgspec
import pytest

from framework.base.common import InstrumentCollection
from framework.base.schema import MessageId, Moments
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.models import OrderbookMsg, TickerMsg, TradeMsg
from framework.base.trading.models import TickerResponse
from framework.binance.stream.handlers import (
    BinanceBBOHandler,
    BinanceOrderbookHandler,
    BinanceTickerHandler,
    BinanceTradesHandler,
)
from framework.binance.stream.models import (
    BookTickerStreamUpdate,
    DiffBookDepthStreamUpdate,
    MarkPriceStreamUpdate,
    TradeStreamUpdate,
)
from framework.binance.trading.exchange import BinanceExchange
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer


class TestBinanceMarketDataStream:
    """Layer 3: Binance market stream message routing."""

    @pytest.mark.asyncio
    async def test_stream_ticker_broadcasts_message(
        self,
        binance_instrument,
    ) -> None:
        """Test mark price stream emits ticker messages.

        Args:
            binance_instrument: Binance instrument fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        exchange = BinanceExchange(
            logger=logger,
            load_secrets=False,
            is_usd_margined=True,
        )
        instrument_collection = InstrumentCollection([binance_instrument])
        handler = BinanceTickerHandler(
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            venue=binance_instrument.venue,
            logger=logger,
            consumer_buffer=queue,
            exchange=exchange,
        )
        ticker_id = MessageId()
        handler._instrument_to_latest_ticker_map[binance_instrument] = TickerResponse(
            id=ticker_id,
            origin_id=ticker_id,
            moments=Moments(),
            instrument=binance_instrument,
            mark_price=0.0,
            index_price=0.0,
            funding_rate=0.0,
            next_funding_time_ms=0.0,
            open_interest=123.0,
            avg_volume_24h=200.0,
            price_chg_24h=1.5,
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

        await handler.decode_and_broadcast(1, encoded)

        assert not queue.is_empty()
        msg = queue.consume()
        assert isinstance(msg, TickerMsg)
        assert msg.instrument.symbol == "BTCUSDT"
        assert msg.open_interest == pytest.approx(123.0)
        assert msg.avg_volume_24h == pytest.approx(200.0)
        assert msg.price_chg_24h_pct == pytest.approx(1.5)

    @pytest.mark.asyncio
    async def test_stream_top_of_orderbook_broadcasts_message(
        self,
        binance_instrument,
    ) -> None:
        """Test book ticker stream emits BBO messages.

        Args:
            binance_instrument: Binance instrument fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        instrument_collection = InstrumentCollection([binance_instrument])
        handler = BinanceBBOHandler(
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            venue=binance_instrument.venue,
            logger=logger,
            consumer_buffer=queue,
        )

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

        await handler.decode_and_broadcast(1, encoded)

        assert not queue.is_empty()
        msg = queue.consume()
        assert isinstance(msg, OrderbookMsg)
        assert msg.is_bbo is True
        assert msg.bids[0].price == pytest.approx(30000.0)

    @pytest.mark.asyncio
    async def test_stream_full_orderbook_broadcasts_message(
        self,
        binance_instrument,
    ) -> None:
        """Test depth stream emits full orderbook messages.

        Args:
            binance_instrument: Binance instrument fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        instrument_collection = InstrumentCollection([binance_instrument])
        handler = BinanceOrderbookHandler(
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            venue=binance_instrument.venue,
            logger=logger,
            consumer_buffer=queue,
        )

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

        await handler.decode_and_broadcast(1, encoded)

        assert not queue.is_empty()
        msg = queue.consume()
        assert isinstance(msg, OrderbookMsg)
        assert msg.is_bbo is False
        assert msg.asks[0].price == pytest.approx(30001.0)

    @pytest.mark.asyncio
    async def test_stream_trades_dedupes_by_trade_id(
        self,
        binance_instrument,
    ) -> None:
        """Test trade stream ignores duplicate trade IDs.

        Args:
            binance_instrument: Binance instrument fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        instrument_collection = InstrumentCollection([binance_instrument])
        handler = BinanceTradesHandler(
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            venue=binance_instrument.venue,
            logger=logger,
            consumer_buffer=queue,
        )

        trade_update = TradeStreamUpdate(
            event_type="trade",
            event_time=2,
            transaction_time=3,
            symbol="BTCUSDT",
            trade_id=10,
            price="30000.0",
            quantity="0.1",
            trade_type="MARKET",
            is_buyer_maker=False,
        )
        encoded_messages = [
            msgspec.json.encode(trade_update),
            msgspec.json.encode(trade_update),
        ]

        await handler.decode_and_broadcast(1, encoded_messages[0])
        await handler.decode_and_broadcast(1, encoded_messages[1])

        messages = []
        while not queue.is_empty():
            messages.append(queue.consume())

        assert len(messages) == 1
        msg = messages[0]
        assert isinstance(msg, TradeMsg)
        assert msg.trades[0].is_buy is True

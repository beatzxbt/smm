"""tests.framework.bybit.stream.test_bybit_market_stream"""

from __future__ import annotations


import msgspec
import pytest

from framework.base.common import InstrumentCollection
from framework.base.stream.connection import WebSocketConnection
from framework.base.stream.models import (
    OrderbookLevel,
    OrderbookMsg,
    TickerMsg,
    TradeMsg,
)
from framework.bybit.stream.handlers import (
    BybitBBOHandler,
    BybitOrderbookHandler,
    BybitTickerHandler,
    BybitTradesHandler,
)
from framework.bybit.stream.models import (
    BybitOrderbookMsg,
    BybitTickerPublicMsg,
    BybitOrderbookPublicMsg,
    BybitTickerMsg,
    BybitTrade,
    BybitTradeMsg,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.ringbuffer import GenericRingBuffer


class TestBybitMarketDataStream:
    """Layer 3: Bybit market stream message routing."""

    @pytest.mark.asyncio
    async def test_stream_ticker_broadcasts_message(
        self,
        bybit_instrument,
    ) -> None:
        """Test ticker stream decodes payloads and broadcasts messages.

        Args:
            bybit_instrument: Bybit instrument fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        instrument_collection = InstrumentCollection([bybit_instrument])
        handler = BybitTickerHandler(
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            venue=bybit_instrument.venue,
            logger=logger,
            consumer_buffer=queue,
        )

        ticker_msg = BybitTickerMsg(
            symbol="BTCUSDT",
            tick_direction="ZeroPlusTick",
            price_24h_pcnt=0.01,
            last_price=30000.0,
            prev_price_24h=29900.0,
            high_price_24h=31000.0,
            low_price_24h=29000.0,
            prev_price_1h=29950.0,
            mark_price=30000.0,
            index_price=29990.0,
            open_interest=1000.0,
            open_interest_value=1000000.0,
            turnover_24h=5000.0,
            volume_24h=1234.0,
            next_funding_time=1234567890,
            funding_rate=0.0001,
        )
        payload = BybitTickerPublicMsg(
            topic="tickers.BTCUSDT",
            type="snapshot",
            data=ticker_msg,
            ts=1234567890,
        )
        encoded = msgspec.json.encode(payload)

        await handler.decode_and_broadcast(1, encoded)

        assert not queue.is_empty()
        msg = queue.consume()
        assert isinstance(msg, TickerMsg)
        assert msg.instrument.symbol == "BTCUSDT"
        assert msg.mark_price == pytest.approx(30000.0)
        assert msg.open_interest == pytest.approx(1000.0)

    @pytest.mark.asyncio
    async def test_stream_orderbook_broadcasts_bbo_and_full(
        self,
        bybit_instrument,
    ) -> None:
        """Test orderbook stream emits both BBO and full depth messages.

        Args:
            bybit_instrument: Bybit instrument fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        instrument_collection = InstrumentCollection([bybit_instrument])
        bbo_handler = BybitBBOHandler(
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            venue=bybit_instrument.venue,
            logger=logger,
            consumer_buffer=queue,
        )
        orderbook_handler = BybitOrderbookHandler(
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            venue=bybit_instrument.venue,
            logger=logger,
            consumer_buffer=queue,
        )

        orderbook_msg = BybitOrderbookMsg(
            symbol="BTCUSDT",
            bids=[OrderbookLevel(price=30000.0, size=1.0)],
            asks=[OrderbookLevel(price=30001.0, size=2.0)],
            update_id=1,
            seq=2,
        )
        payloads = [
            BybitOrderbookPublicMsg(
                topic="orderbook.1.BTCUSDT",
                type="snapshot",
                data=orderbook_msg,
                ts=1,
            ),
            BybitOrderbookPublicMsg(
                topic="orderbook.1000.BTCUSDT",
                type="snapshot",
                data=orderbook_msg,
                ts=1,
            ),
        ]
        encoded_messages = [msgspec.json.encode(payload) for payload in payloads]

        await bbo_handler.decode_and_broadcast(1, encoded_messages[0])
        await orderbook_handler.decode_and_broadcast(1, encoded_messages[1])

        messages = []
        while not queue.is_empty():
            messages.append(queue.consume())

        assert len(messages) == 2
        assert all(isinstance(msg, OrderbookMsg) for msg in messages)
        assert messages[0].is_bbo is True
        assert messages[1].is_bbo is False
        assert messages[0].is_snapshot is True
        assert messages[1].is_snapshot is True

    @pytest.mark.asyncio
    async def test_stream_trades_dedupes_by_seq(
        self,
        bybit_instrument,
    ) -> None:
        """Test trade stream skips duplicate sequence IDs.

        Args:
            bybit_instrument: Bybit instrument fixture.
        """
        queue = GenericRingBuffer(16)
        logger = Logger(name="test")
        instrument_collection = InstrumentCollection([bybit_instrument])
        handler = BybitTradesHandler(
            connection=WebSocketConnection("wss://example.test", logger),
            instrument_collection=instrument_collection,
            venue=bybit_instrument.venue,
            logger=logger,
            consumer_buffer=queue,
        )

        trade = BybitTrade(
            time_ms=1234567890000,
            symbol="BTCUSDT",
            side="Buy",
            size=0.1,
            price=30000.0,
            id="trade_1",
            seq=1,
        )
        payloads = [
            BybitTradeMsg(
                topic="publicTrade.BTCUSDT",
                type="snapshot",
                ts=1234567890,
                data=[trade],
            ),
            BybitTradeMsg(
                topic="publicTrade.BTCUSDT",
                type="snapshot",
                ts=1234567891,
                data=[trade],
            ),
        ]
        encoded_messages = [msgspec.json.encode(payload) for payload in payloads]

        await handler.decode_and_broadcast(1, encoded_messages[0])
        await handler.decode_and_broadcast(1, encoded_messages[1])

        messages = []
        while not queue.is_empty():
            messages.append(queue.consume())

        assert len(messages) == 1
        msg = messages[0]
        assert isinstance(msg, TradeMsg)
        assert len(msg.trades) == 1
        assert msg.trades[0].price == pytest.approx(30000.0)

"""tests.framework.bybit.stream.test_bybit_market_stream"""

from __future__ import annotations

import asyncio

import msgspec
import pytest

from framework.base.stream.models import OrderbookMsg, TickerMsg, TradeMsg
from framework.bybit.stream.market import BybitMarketDataStream
from framework.bybit.stream.structs import (
    BybitOrderbookLevel,
    BybitOrderbookMsg,
    BybitPublicMsg,
    BybitTickerMsg,
    BybitTradeMsg,
    BybitTradePublicMsg,
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


class TestBybitMarketDataStream:
    """Layer 3: Bybit market stream message routing."""

    @pytest.mark.asyncio
    async def test_stream_ticker_broadcasts_message(
        self,
        bybit_instrument,
        monkeypatch,
    ) -> None:
        """Test ticker stream decodes payloads and broadcasts messages.

        Args:
            bybit_instrument: Bybit instrument fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        queue = asyncio.Queue()
        stream = BybitMarketDataStream(
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )
        stream._instruments = [bybit_instrument]

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
        payload = BybitPublicMsg(
            topic="tickers.BTCUSDT",
            type="snapshot",
            data=ticker_msg,
            ts=1234567890,
        )
        encoded = msgspec.json.encode(payload)

        monkeypatch.setattr(
            "framework.bybit.stream.market.WsSingle",
            make_fake_ws_single([encoded]),
        )

        await stream.stream_ticker([bybit_instrument])

        assert not queue.empty()
        msg = queue.get_nowait()
        assert isinstance(msg, TickerMsg)
        assert msg.instrument.symbol == "BTCUSDT"
        assert msg.mark_price == pytest.approx(30000.0)
        assert msg.open_interest == pytest.approx(1000.0)

    @pytest.mark.asyncio
    async def test_stream_orderbook_broadcasts_bbo_and_full(
        self,
        bybit_instrument,
        monkeypatch,
    ) -> None:
        """Test orderbook stream emits both BBO and full depth messages.

        Args:
            bybit_instrument: Bybit instrument fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        queue = asyncio.Queue()
        stream = BybitMarketDataStream(
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )
        stream._instruments = [bybit_instrument]

        orderbook_msg = BybitOrderbookMsg(
            symbol="BTCUSDT",
            bids=[BybitOrderbookLevel(price=30000.0, size=1.0)],
            asks=[BybitOrderbookLevel(price=30001.0, size=2.0)],
            update_id=1,
            seq=2,
        )
        payloads = [
            BybitPublicMsg(
                topic="orderbook.1.BTCUSDT",
                type="snapshot",
                data=orderbook_msg,
                ts=1,
            ),
            BybitPublicMsg(
                topic="orderbook.500.BTCUSDT",
                type="snapshot",
                data=orderbook_msg,
                ts=1,
            ),
        ]
        encoded_messages = [msgspec.json.encode(payload) for payload in payloads]

        monkeypatch.setattr(
            "framework.bybit.stream.market.WsSingle",
            make_fake_ws_single(encoded_messages),
        )

        await stream.stream_orderbook([bybit_instrument])

        messages = []
        while not queue.empty():
            messages.append(queue.get_nowait())

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
        monkeypatch,
    ) -> None:
        """Test trade stream skips duplicate sequence IDs.

        Args:
            bybit_instrument: Bybit instrument fixture.
            monkeypatch: Pytest monkeypatch fixture.
        """
        queue = asyncio.Queue()
        stream = BybitMarketDataStream(
            logger=Logger(name="test"),
            consumer_queues=[queue],
        )
        stream._instruments = [bybit_instrument]

        trade = BybitTradeMsg(
            time_ms=1234567890000,
            symbol="BTCUSDT",
            side="Buy",
            size=0.1,
            price=30000.0,
            id="trade_1",
            seq=1,
        )
        payloads = [
            BybitTradePublicMsg(
                topic="publicTrade.BTCUSDT",
                type="snapshot",
                ts=1234567890,
                data=[trade],
            ),
            BybitTradePublicMsg(
                topic="publicTrade.BTCUSDT",
                type="snapshot",
                ts=1234567891,
                data=[trade],
            ),
        ]
        encoded_messages = [msgspec.json.encode(payload) for payload in payloads]

        monkeypatch.setattr(
            "framework.bybit.stream.market.WsSingle",
            make_fake_ws_single(encoded_messages),
        )

        await stream.stream_trades([bybit_instrument])

        messages = []
        while not queue.empty():
            messages.append(queue.get_nowait())

        assert len(messages) == 1
        msg = messages[0]
        assert isinstance(msg, TradeMsg)
        assert len(msg.trades) == 1
        assert msg.trades[0].price == pytest.approx(30000.0)

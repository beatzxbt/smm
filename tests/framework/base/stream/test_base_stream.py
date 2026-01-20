"""tests.framework.base.stream.test_base_stream"""

from __future__ import annotations

import asyncio

import pytest

from framework.base.common import (
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Venue,
)
from framework.base.stream.models import HeartbeatMsg, MarketDataStreamType
from framework.base.stream.stream import DataStream
from mm_toolbox.logging.standard import Logger


class DummyStream(DataStream):
    """Minimal DataStream implementation for testing.

    Args:
        logger: Logger instance for the stream.
        consumer_queues: Queues receiving broadcast messages.
    """

    def __init__(
        self,
        logger: Logger,
        consumer_queues: list[asyncio.Queue],
    ) -> None:
        super().__init__(
            venue=Venue.BINANCE_USDM,
            logger=logger,
            consumer_queues=consumer_queues,
        )
        self.populate_calls = 0

    def populate_instrument_collection(self, collection: InstrumentCollection) -> None:
        """Populate the collection with tracked instruments.

        Args:
            collection: Collection to populate.
        """
        self.populate_calls += 1
        for instrument in self._instruments:
            collection.add(instrument)


class TestDataStreamInstrumentCollection:
    """Layer 1: Instrument collection behavior."""

    def test_instrument_collection_is_lazy(self, test_logger: Logger) -> None:
        """Test collection initialization happens once and is cached.

        Args:
            test_logger: Logger fixture for the stream.
        """
        stream = DummyStream(logger=test_logger, consumer_queues=[])
        stream._instruments = [
            Instrument(
                venue=Venue.BINANCE_USDM,
                symbol="BTCUSDT",
                base="BTC",
                quote="USDT",
                code=0,
                instrument_type=InstrumentType.PERPETUAL,
            )
        ]

        collection_first = stream.instrument_collection
        collection_second = stream.instrument_collection

        assert collection_first is collection_second
        assert stream.populate_calls == 1
        assert collection_first.get(Venue.BINANCE_USDM, "BTCUSDT") is not None


class TestDataStreamBroadcast:
    """Layer 1: Broadcast fanout behavior."""

    def test_broadcast_fans_out(self, test_logger: Logger) -> None:
        """Test broadcast enqueues messages in all queues.

        Args:
            test_logger: Logger fixture for the stream.
        """
        queues = [asyncio.Queue(), asyncio.Queue()]
        stream = DummyStream(logger=test_logger, consumer_queues=queues)

        msg = HeartbeatMsg(
            venue=Venue.BINANCE_USDM,
            stream_type=MarketDataStreamType.TICKER,
            time_now_ms=1,
            time_next_check_ms=2,
        )
        stream.broadcast(msg)

        assert queues[0].get_nowait() == msg
        assert queues[1].get_nowait() == msg


class TestDataStreamHeartbeat:
    """Layer 2: Heartbeat broadcasting behavior."""

    @pytest.mark.asyncio
    async def test_broadcast_heartbeat_emits_messages(
        self, monkeypatch, test_logger: Logger
    ) -> None:
        """Test heartbeat task emits HeartbeatMsg with expected timing fields.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
            test_logger: Logger fixture for the stream.
        """
        queue = asyncio.Queue()
        stream = DummyStream(logger=test_logger, consumer_queues=[queue])
        stream.is_running = True

        original_sleep = asyncio.sleep

        async def _fast_sleep(_seconds: float) -> None:
            """Fast sleep stub for heartbeat test.

            Args:
                _seconds: Sleep duration placeholder.
            """
            await original_sleep(0)

        monkeypatch.setattr("framework.base.stream.stream.asyncio.sleep", _fast_sleep)
        monkeypatch.setattr("framework.base.stream.stream.time_ms", lambda: 123456)

        task = asyncio.create_task(
            stream.broadcast_heartbeat(MarketDataStreamType.TICKER, interval_s=1)
        )
        msg = await asyncio.wait_for(queue.get(), timeout=0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert isinstance(msg, HeartbeatMsg)
        assert msg.stream_type == MarketDataStreamType.TICKER
        assert msg.time_now_ms == 123456
        assert msg.time_next_check_ms == 124456

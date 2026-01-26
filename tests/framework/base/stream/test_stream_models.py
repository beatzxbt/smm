"""Tests for stream event models."""

from __future__ import annotations

from framework.base.common import Instrument, InstrumentType, Venue
from framework.base.stream.models import (
    DataStreamEvent,
    DataStreamEventMsg,
    MarketDataStreamType,
)


class TestDataStreamEvent:
    """DataStreamEvent enum values."""

    def test_event_values(self) -> None:
        """Test DataStreamEvent exposes expected values.

        Returns:
            None.
        """
        assert DataStreamEvent.START.value == "START"
        assert DataStreamEvent.STOP.value == "STOP"
        assert DataStreamEvent.SUBSCRIBE.value == "SUBSCRIBE"
        assert DataStreamEvent.UNSUBSCRIBE.value == "UNSUBSCRIBE"
        assert DataStreamEvent.HEARTBEAT.value == "HEARTBEAT"


class TestDataStreamEventMsg:
    """DataStreamEventMsg construction."""

    def test_event_msg_fields(self) -> None:
        """Test DataStreamEventMsg preserves input fields.

        Returns:
            None.
        """
        instrument = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        msg = DataStreamEventMsg(
            venue=Venue.BINANCE_USDM,
            event=DataStreamEvent.SUBSCRIBE,
            changes={MarketDataStreamType.TICKER: instrument},
            state={MarketDataStreamType.TICKER: instrument},
            time_ms=123456,
        )

        assert msg.venue == Venue.BINANCE_USDM
        assert msg.event == DataStreamEvent.SUBSCRIBE
        assert msg.changes == {MarketDataStreamType.TICKER: instrument}
        assert msg.state == {MarketDataStreamType.TICKER: instrument}
        assert msg.time_ms == 123456

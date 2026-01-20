"""Tests for framework.loader venue bundle loading."""

from __future__ import annotations

import pytest

from framework.base.common import Venue
from framework.base.stream.market import MarketDataStream
from framework.base.stream.private import PrivateDataStream
from framework.base.trading.exchange import Exchange
from framework.loader import load_venue_bundle


class TestVenueBundleLoading:
    """Layer 1: Venue bundle resolution."""

    def test_load_bybit_bundle(self):
        """Test Bybit bundle resolves expected class types."""
        bundle = load_venue_bundle(Venue.BYBIT)
        assert issubclass(bundle.exchange, Exchange)
        assert issubclass(bundle.market_data_stream, MarketDataStream)
        assert issubclass(bundle.private_data_stream, PrivateDataStream)

    def test_load_binance_bundle(self):
        """Test Binance bundle resolves expected class types."""
        bundle = load_venue_bundle(Venue.BINANCE_USDM)
        assert issubclass(bundle.exchange, Exchange)
        assert issubclass(bundle.market_data_stream, MarketDataStream)
        assert issubclass(bundle.private_data_stream, PrivateDataStream)

    def test_unknown_venue_raises(self):
        """Test unsupported venues raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported venue"):
            load_venue_bundle(Venue.OKX)

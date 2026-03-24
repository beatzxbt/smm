"""Tests for framework.loader venue bundle loading."""

from __future__ import annotations

import pytest

from framework.base.common import Venue
from framework.base.stream.manager import MarketStreamManager, PrivateStreamManager
from framework.base.trading.exchange import Exchange
from framework.loader import load_venue_bundle


class TestVenueBundleLoading:
    """Layer 1: Venue bundle resolution."""

    def test_load_bybit_bundle(self):
        """Test Bybit bundle resolves expected class types."""
        bundle = load_venue_bundle(Venue.BYBIT)
        assert issubclass(bundle.exchange, Exchange)
        assert issubclass(bundle.market_stream_manager, MarketStreamManager)
        assert issubclass(bundle.private_stream_manager, PrivateStreamManager)

    def test_load_binance_bundle(self):
        """Test Binance bundle resolves expected class types."""
        bundle = load_venue_bundle(Venue.BINANCE_USDM)
        assert issubclass(bundle.exchange, Exchange)
        assert issubclass(bundle.market_stream_manager, MarketStreamManager)
        assert issubclass(bundle.private_stream_manager, PrivateStreamManager)

    def test_null_venue_raises_value_error(self):
        """Test NULL venue raises ValueError as invalid input."""
        with pytest.raises(ValueError, match="Venue.NULL is not a valid venue"):
            load_venue_bundle(Venue.NULL)

    @pytest.mark.parametrize(
        "unsupported_venue",
        [Venue.ZERO_ONE, Venue.DECIBEL, Venue.HOTSTUFF],
    )
    def test_unimplemented_venue_raises_not_implemented_error(
        self, unsupported_venue: Venue
    ):
        """Test unsupported non-NULL venues raise NotImplementedError."""
        with pytest.raises(
            NotImplementedError,
            match="No venue bundle implementation for venue",
        ):
            load_venue_bundle(unsupported_venue)

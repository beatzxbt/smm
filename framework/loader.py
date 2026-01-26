"""Venue bundle loader for exchange components.

Usage: resolve exchange and stream manager classes for a given venue.
Components: VenueBundle and lazy imports for exchange-specific managers.
"""

from __future__ import annotations

from typing import NamedTuple, Type

from framework.base.common import Venue
from framework.base.stream.manager import MarketStreamManager, PrivateStreamManager
from framework.base.trading.exchange import Exchange


class VenueBundle(NamedTuple):
    """A bundle of exchange class types for a given venue."""

    exchange: Type[Exchange]
    market_stream_manager: Type[MarketStreamManager]
    private_stream_manager: Type[PrivateStreamManager]


def load_venue_bundle(venue: Venue) -> VenueBundle:
    """Lazily load exchange classes for a given venue.

    Args:
        venue: Venue identifier.

    Returns:
        VenueBundle: Bundle of exchange and stream manager classes.
    """
    match venue:
        case Venue.BINANCE_USDM | Venue.BINANCE_COINM:
            from framework.binance.stream.manager import (
                BinanceMarketStreamManager,
                BinancePrivateStreamManager,
            )
            from framework.binance.trading.exchange import BinanceExchange

            return VenueBundle(
                exchange=BinanceExchange,
                market_stream_manager=BinanceMarketStreamManager,
                private_stream_manager=BinancePrivateStreamManager,
            )
        case Venue.BYBIT:
            from framework.bybit.stream.manager import (
                BybitMarketStreamManager,
                BybitPrivateStreamManager,
            )
            from framework.bybit.trading.exchange import BybitExchange

            return VenueBundle(
                exchange=BybitExchange,
                market_stream_manager=BybitMarketStreamManager,
                private_stream_manager=BybitPrivateStreamManager,
            )
        case Venue.OKX:
            from framework.okx.stream.manager import (
                OkxMarketStreamManager,
                OkxPrivateStreamManager,
            )
            from framework.okx.trading.exchange import OkxExchange

            return VenueBundle(
                exchange=OkxExchange,
                market_stream_manager=OkxMarketStreamManager,
                private_stream_manager=OkxPrivateStreamManager,
            )

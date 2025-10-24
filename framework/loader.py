from typing import Type, NamedTuple

from framework.base.common import Venue
from framework.base.stream.market import MarketDataStream
from framework.base.stream.private import PrivateDataStream
from framework.base.trading.exchange import Exchange


class VenueBundle(NamedTuple):
    """A bundle of exchange class types for a given venue."""
    exchange: Type[Exchange]
    market_data_stream: Type[MarketDataStream]
    private_data_stream: Type[PrivateDataStream]


def load_venue_bundle(venue: Venue) -> VenueBundle:
    """Lazily load exchange classes for a given venue."""
    match venue:
        case Venue.BINANCE_USDM | Venue.BINANCE_COINM:
            from framework.binance.stream.market import BinanceMarketDataStream
            from framework.binance.stream.private import BinancePrivateDataStream
            from framework.binance.trading.exchange import BinanceExchange

            return VenueBundle(
                exchange=BinanceExchange,
                market_data_stream=BinanceMarketDataStream,
                private_data_stream=BinancePrivateDataStream,
            )
        case Venue.BYBIT:
            from framework.bybit.stream.market import BybitMarketDataStream
            from framework.bybit.stream.private import BybitPrivateDataStream
            from framework.bybit.trading.exchange import BybitExchange

            return VenueBundle(
                exchange=BybitExchange,
                market_data_stream=BybitMarketDataStream,
                private_data_stream=BybitPrivateDataStream,
            )
        case _:
            raise ValueError(f"Unsupported venue; {venue}")
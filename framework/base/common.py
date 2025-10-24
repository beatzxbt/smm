from enum import StrEnum
from typing import Self

from msgspec import Struct


class Venue(StrEnum):
    """Represents a venue (exchange)."""

    NULL = "NULL"  # Used when value is not required/known
    BINANCE_USDM = "BinanceUSDM"
    BINANCE_COINM = "BinanceCOINM"
    BYBIT = "Bybit"
    OKX = "OKX"


class InstrumentType(StrEnum):
    """Represents the type of instrument."""

    NULL = "NULL"  # Used when value is not required/known
    SPOT = "Spot"
    FUTURE = "Future"
    PERPETUAL = "Perpetual"


class Instrument(Struct, frozen=True):
    """Represents an instrument on an exchange."""

    venue: Venue
    base: str
    quote: str
    symbol: str # Exchange specific version of the instrument (eg "BTCUSDT", "BTC-USDT", "BTC/USDT")
    instrument_type: InstrumentType

    @classmethod
    def empty(cls) -> Self:
        """Returns an empty instrument, when value is not required/known."""
        return cls(
            venue=Venue.NULL, base="", quote="", symbol="", instrument_type=InstrumentType.NULL
        )

    @classmethod
    def from_str(cls, instrument: str) -> Self:
        """Create an instrument from a string seperated by hyphens."""
        venue, base, quote, symbol, instrument_type = instrument.split("-")
        return cls(
            venue=Venue(venue),
            base=base,
            quote=quote,
            symbol=symbol,
            instrument_type=InstrumentType(instrument_type),
        )

    def __str__(self):
        return f"{self.venue.value}-{self.base}-{self.quote}-{self.symbol}-{self.instrument_type.value}".upper()


class SimpleCache[K: str, V: int | float]:
    """Simple wrapper around dict to check for changed number values.

    As hardcoded behaviour, it updates the cache with the new value if any
    comparison functions are called. If the value doesn't exist, it is considered
    different and is also added to the cache.

    This may be used for things like sequence ids of various symbols.

    Watch out for memory usage if you have a ton of keys!
    """

    def __init__(self):
        self.cache: dict[K, V] = {}

    def is_different(self, key: K, new_value: V) -> bool:
        result = True
        if value := self.cache.get(key, None):
            result = value != new_value
        self.cache[key] = new_value
        return result

    def is_higher(self, key: K, new_value: V) -> bool:
        result = True
        if value := self.cache.get(key, None):
            result = value < new_value
        self.cache[key] = new_value
        return result

    def is_lower(self, key: K, new_value: V) -> bool:
        result = True
        if value := self.cache.get(key, None):
            result = value > new_value
        self.cache[key] = new_value
        return result

    def clear(self):
        self.cache.clear()
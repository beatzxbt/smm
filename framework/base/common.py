"""Core common types and utilities.

Defines exchange primitives (Venue, InstrumentType, Instrument), the
InstrumentCollection container, and the SimpleMap bi-directional mapping.
"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from typing import Self, Iterable, Iterator, TypeVar, Generic, cast

from msgspec import Struct


Symbol = str  # Type alias for venue-specific symbol strings

K = TypeVar("K")
V = TypeVar("V")


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
    symbol: str  # Exchange specific (eg "BTCUSDT", "BTC-USDT", "BTC/USDT")
    code: int  # Some exchanges use market ids alongside a symbol
    instrument_type: InstrumentType

    @classmethod
    def empty(cls) -> Self:
        """Returns an empty instrument, when value is not required/known."""
        return cls(
            venue=Venue.NULL,
            base="",
            quote="",
            symbol="",
            code=0,
            instrument_type=InstrumentType.NULL,
        )

    def __str__(self):
        return f"{self.venue.value}:{self.base}/{self.quote}:{self.instrument_type.value}".upper()


class InstrumentCollection:
    """Collection of instruments with filtering and grouping capabilities."""

    def __init__(self, instruments: Iterable[Instrument] | None = None):
        self._instruments: set[Instrument] = set(instruments) if instruments else set()

        # Map (venue, symbol) -> Instrument (Unique)
        self._venue_symbol_map: dict[tuple[Venue, str], Instrument] = {
            (i.venue, i.symbol): i for i in self._instruments
        }

        self._by_venue: dict[Venue, list[Instrument]] = defaultdict(list)
        for i in self._instruments:
            self._by_venue[i.venue].append(i)

    @property
    def instruments(self) -> list[Instrument]:
        return list(self._instruments)

    @property
    def venues(self) -> set[Venue]:
        return set(self._by_venue.keys())

    def add(self, instrument: Instrument) -> None:
        if instrument in self._instruments:
            return
        self._instruments.add(instrument)
        self._venue_symbol_map[(instrument.venue, instrument.symbol)] = instrument
        self._by_venue[instrument.venue].append(instrument)

    def get(self, venue: Venue, symbol: str) -> Instrument | None:
        """Fast lookup for an instrument by venue and symbol."""
        return self._venue_symbol_map.get((venue, symbol), None)

    def get_by_venue(self, venue: Venue) -> list[Instrument]:
        return self._by_venue[venue]

    def remove(self, instrument: Instrument) -> None:
        if instrument not in self._instruments:
            return
        self._instruments.remove(instrument)
        self._venue_symbol_map.pop((instrument.venue, instrument.symbol))
        self._by_venue[instrument.venue].remove(instrument)

    def merge(self, other: "InstrumentCollection") -> None:
        """Merges another InstrumentCollection into this one."""
        for instrument in other.instruments:
            self.add(instrument)

    def filter(
        self,
        venues: Iterable[Venue] | None = None,
        bases: Iterable[str] | None = None,
        quotes: Iterable[str] | None = None,
        instrument_types: Iterable[InstrumentType] | None = None,
        base_blacklist: Iterable[str] | None = None,
        quote_blacklist: Iterable[str] | None = None,
    ) -> list[Instrument]:
        """Filters instruments based on provided criteria."""
        venue_set = set(venues) if venues else None
        base_set = set(bases) if bases else None
        quote_set = set(quotes) if quotes else None
        type_set = set(instrument_types) if instrument_types else None
        base_bl = set(base_blacklist) if base_blacklist else set()
        quote_bl = set(quote_blacklist) if quote_blacklist else set()

        result: list[Instrument] = []
        for i in self._instruments:
            if venue_set and i.venue not in venue_set:
                continue
            if base_set and i.base not in base_set:
                continue
            if quote_set and i.quote not in quote_set:
                continue
            if type_set and i.instrument_type not in type_set:
                continue
            if i.base in base_bl:
                continue
            if i.quote in quote_bl:
                continue
            result.append(i)
        return result

    def is_empty(self) -> bool:
        """Return whether the collection is empty.

        Returns:
            bool: True if the collection has no instruments, otherwise False.
        """
        return not self._instruments

    def __iter__(self) -> Iterator[Instrument]:
        return iter(self._instruments)

    def __len__(self) -> int:
        return len(self._instruments)

    def __contains__(self, instrument: Instrument) -> bool:
        return instrument in self._instruments


class SimpleMap(Generic[K, V]):
    """Simple K<->V bi-directional mapping implementation.

    Makes it simpler to use a map with both keys and values.

    Supports (map=SimpleMap()):
        map[key] or map[value] -> value or key
        map[key] = value -> map[value] = key
        map[value] = key -> map[key] = value
        key in map or value in map -> bool
        del map[key] or del map[value] -> None

    Args:
        items: A dictionary of items to initialize the map with.

    Returns:
        A SimpleMap instance.
    """

    def __init__(self, items: dict[K, V]) -> None:
        self._k_to_v_map: dict[K, V] = items
        self._v_to_k_map: dict[V, K] = {v: k for k, v in items.items()}

    def get(self, key: K | V) -> V | K | None:
        """Get value by key or value, returning None if not found."""
        if key in self._k_to_v_map:
            return self._k_to_v_map[cast(K, key)]
        elif key in self._v_to_k_map:
            return self._v_to_k_map[cast(V, key)]
        return None

    def __getitem__(self, key: K | V) -> V | K:
        if key in self._k_to_v_map:
            return self._k_to_v_map[cast(K, key)]
        elif key in self._v_to_k_map:
            return self._v_to_k_map[cast(V, key)]
        else:
            raise KeyError(f"Key {key} not found in map")

    def __setitem__(self, key: K, value: V) -> None:
        """Set a key/value pair while keeping both maps consistent.

        Args:
            key: Key to associate with the value.
            value: Value to associate with the key.
        """
        if key in self._k_to_v_map:
            old_value = self._k_to_v_map[key]
            if self._v_to_k_map.get(old_value) == key:
                del self._v_to_k_map[old_value]

        if value in self._v_to_k_map:
            old_key = self._v_to_k_map[value]
            if self._k_to_v_map.get(old_key) == value:
                del self._k_to_v_map[old_key]

        self._k_to_v_map[key] = value
        self._v_to_k_map[value] = key

    def __contains__(self, key: K | V) -> bool:
        return key in self._k_to_v_map or key in self._v_to_k_map

    def __delitem__(self, key: K | V) -> None:
        """Delete a key or value and its corresponding pair.

        Args:
            key: Key or value to remove from the mapping.

        Raises:
            KeyError: If the key/value does not exist in the map.
        """
        if key in self._k_to_v_map:
            cast_key = cast(K, key)
            value = self._k_to_v_map[cast_key]
            del self._k_to_v_map[cast_key]
            if self._v_to_k_map.get(value) == key:
                del self._v_to_k_map[value]
            return
        if key in self._v_to_k_map:
            cast_key = cast(V, key)
            paired_key = self._v_to_k_map[cast_key]
            del self._v_to_k_map[cast_key]
            if self._k_to_v_map.get(paired_key) == key:
                del self._k_to_v_map[paired_key]
            return
        raise KeyError(f"Key {key} not found in map")

    def __len__(self) -> int:
        return len(self._k_to_v_map)

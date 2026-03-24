"""Core common types and utilities.

Defines exchange primitives (Venue, InstrumentType, Instrument) and the
InstrumentCollection container.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Iterable, Iterator, NewType, Self

from msgspec import Struct


class Venue(StrEnum):
    """Represents a venue (exchange)."""

    NULL = "Null"  # Used when value is not required/known
    BINANCE_USDM = "BinanceUsdM"
    BINANCE_COINM = "BinanceCoinM"
    BYBIT = "Bybit"
    OKX = "Okx"
    ZERO_ONE = "01"
    DECIBEL = "Decibel"
    HOTSTUFF = "Hotstuff"


class InstrumentType(StrEnum):
    """Represents the type of instrument."""

    NULL = "NULL"  # Used when value is not required/known
    SPOT = "Spot"
    PERPETUAL = "Perpetual"


Asset = str
Symbol = str
OrderId = NewType("OrderId", str)
ClientOrderId = NewType("ClientOrderId", str)


class Instrument(Struct, frozen=True):
    """Represents an instrument on an exchange."""

    venue: Venue
    base: Asset
    quote: Asset
    symbol: Symbol  # Exchange specific (eg "BTCUSDT", "BTC-USDT", "BTC/USDT")
    code: int | str  # Some exchanges use market ids alongside/replacing a symbol
    instrument_type: InstrumentType
    tick_size: float  # Minimum price increment
    lot_size: float  # Minimum size increment

    def __post_init__(self) -> None:
        # Individual instrument case.
        if self.venue != Venue.NULL and self.instrument_type != InstrumentType.NULL:
            if not self.symbol:
                raise ValueError("symbol must be non-empty for non-NULL instruments")
            if not self.base or self.base not in self.symbol:
                raise ValueError(
                    "base must be present in symbol for non-NULL instruments"
                )
            if not self.quote or self.quote not in self.symbol:
                raise ValueError(
                    "quote must be present in symbol for non-NULL instruments"
                )

            if self.tick_size <= 0.0:
                raise ValueError("tick_size must be > 0 for non-NULL instruments")
            if self.lot_size <= 0.0:
                raise ValueError("lot_size must be > 0 for non-NULL instruments")

        # Generic Instrument case (filler to provide Venue details)
        elif self.venue != Venue.NULL and self.instrument_type == InstrumentType.NULL:
            if self.symbol:
                raise ValueError("symbol must be empty when instrument_type is NULL")
            if self.base:
                raise ValueError("base must be empty when instrument_type is NULL")
            if self.quote:
                raise ValueError("quote must be empty when instrument_type is NULL")

        # Totally empty case, all fields must match defaults
        else:
            # Fill in.
            ...

    @classmethod
    @lru_cache(maxsize=2048)
    def empty_with(
        cls,
        venue: Venue = Venue.NULL,
        base: str = "",
        quote: str = "",
        symbol: str = "",
        code: int = 0,
        instrument_type: InstrumentType = InstrumentType.NULL,
        tick_size: float = 0.0,
        lot_size: float = 0.0,
    ) -> Self:
        """Return an instrument with empty defaults and optional overrides.

        Args:
            venue: Venue override.
            base: Base asset override.
            quote: Quote asset override.
            symbol: Symbol override.
            code: Exchange-specific code override.
            instrument_type: Instrument type override.
            tick_size: Minimum price increment override.
            lot_size: Minimum size increment override.

        Returns:
            Self: Instrument with provided values and empty defaults.
        """
        return cls(
            venue=venue,
            base=base,
            quote=quote,
            symbol=symbol,
            code=code,
            instrument_type=instrument_type,
            tick_size=tick_size,
            lot_size=lot_size,
        )

    @classmethod
    def empty(cls) -> Self:
        """Returns an empty instrument, when value is not required/known."""
        return cls.empty_with()

    def __str__(self):
        return f"{self.venue.value}:{self.base}/{self.quote}:{self.instrument_type.value}".upper()


class InstrumentCollection:
    """Immutable, single-venue collection of instruments."""

    def __init__(self, instruments: Iterable[Instrument]):
        unique_instruments: list[Instrument] = []
        instrument_set: set[Instrument] = set()
        for instrument in instruments:
            if instrument in instrument_set:
                continue
            instrument_set.add(instrument)
            unique_instruments.append(instrument)

        venue: Venue | None = None
        symbol_map: dict[Symbol, Instrument] = {}
        for instrument in unique_instruments:
            if venue is None:
                venue = instrument.venue
            elif instrument.venue != venue:
                raise ValueError(
                    "InstrumentCollection supports a single venue only; "
                    f"found '{venue}' and '{instrument.venue}'"
                )
            if (
                instrument.symbol in symbol_map
                and symbol_map[instrument.symbol] != instrument
            ):
                raise ValueError(
                    "InstrumentCollection requires unique symbols within a venue; "
                    f"duplicate symbol '{instrument.symbol}'"
                )
            symbol_map[instrument.symbol] = instrument

        self._venue = venue
        self._instruments = tuple(unique_instruments)
        self._instrument_set: frozenset[Instrument] = frozenset(unique_instruments)
        self._symbol_map = symbol_map

    @property
    def instruments(self) -> list[Instrument]:
        return list(self._instruments)

    @property
    def venue(self) -> Venue | None:
        return self._venue

    @lru_cache(maxsize=4096)
    def get(self, symbol: Symbol) -> Instrument | None:
        """Fast lookup for an instrument by symbol.

        Args:
            symbol: Venue-specific symbol to resolve.

        Returns:
            Instrument | None: Matching instrument, or None if not found.
        """
        return self._symbol_map.get(symbol, None)

    def filter(
        self,
        bases: Iterable[str] | None = None,
        quotes: Iterable[str] | None = None,
        instrument_types: Iterable[InstrumentType] | None = None,
        base_blacklist: Iterable[str] | None = None,
        quote_blacklist: Iterable[str] | None = None,
    ) -> list[Instrument]:
        """Filters instruments based on provided criteria."""
        base_set = set(bases) if bases else None
        quote_set = set(quotes) if quotes else None
        type_set = set(instrument_types) if instrument_types else None
        base_bl = set(base_blacklist) if base_blacklist else set()
        quote_bl = set(quote_blacklist) if quote_blacklist else set()

        result: list[Instrument] = []
        for i in self._instruments:
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

    def __iter__(self) -> Iterator[Instrument]:
        return iter(self._instruments)

    def __len__(self) -> int:
        return len(self._instruments)

    def __contains__(self, instrument: Instrument) -> bool:
        return instrument in self._instrument_set


__all__ = [
    "Venue",
    "InstrumentType",
    "Asset",
    "Symbol",
    "OrderId",
    "ClientOrderId",
    "Instrument",
    "InstrumentCollection",
]

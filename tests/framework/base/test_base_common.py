"""Tests for framework.base.common module.

Tests cover:
- Venue enum (exchange identifiers)
- InstrumentType enum (instrument classifications)
- Instrument struct validation and operations
- SimpleMap bidirectional mapping
- InstrumentCollection filtering and grouping

Tests are organized by dependency layer:
1. Primitives: Venue, InstrumentType, Instrument, SimpleMap
2. Composites: InstrumentCollection
"""

from __future__ import annotations

import pytest

from framework.base.common import (
    Instrument,
    InstrumentCollection,
    InstrumentType,
    SimpleMap,
    Venue,
)


class TestVenue:
    """Test Venue enum."""

    def test_enum_values_exist(self):
        """Test all expected venue values exist."""
        assert Venue.NULL == "NULL"
        assert Venue.BINANCE_USDM == "BinanceUSDM"
        assert Venue.BINANCE_COINM == "BinanceCOINM"
        assert Venue.BYBIT == "Bybit"
        assert Venue.OKX == "OKX"

    def test_str_representation(self):
        """Test venue string representation."""
        assert str(Venue.BINANCE_USDM) == "BinanceUSDM"
        assert str(Venue.BYBIT) == "Bybit"
        assert str(Venue.NULL) == "NULL"

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert Venue.BINANCE_USDM in Venue
        assert Venue.BYBIT in Venue
        assert "InvalidVenue" not in [v.value for v in Venue]


class TestInstrumentType:
    """Test InstrumentType enum."""

    def test_enum_values_exist(self):
        """Test all expected instrument type values exist."""
        assert InstrumentType.NULL == "NULL"
        assert InstrumentType.SPOT == "Spot"
        assert InstrumentType.FUTURE == "Future"
        assert InstrumentType.PERPETUAL == "Perpetual"

    def test_str_representation(self):
        """Test instrument type string representation."""
        assert str(InstrumentType.SPOT) == "Spot"
        assert str(InstrumentType.PERPETUAL) == "Perpetual"
        assert str(InstrumentType.NULL) == "NULL"

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert InstrumentType.PERPETUAL in InstrumentType
        assert InstrumentType.SPOT in InstrumentType
        assert "Invalid" not in [t.value for t in InstrumentType]


class TestInstrument:
    """Test Instrument struct creation and basic operations."""

    def test_creation_with_valid_data(self):
        """Test creating instrument with valid data."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        assert inst.venue == Venue.BINANCE_USDM
        assert inst.base == "BTC"
        assert inst.quote == "USDT"
        assert inst.symbol == "BTCUSDT"
        assert inst.code == 1
        assert inst.instrument_type == InstrumentType.PERPETUAL

    def test_frozen_immutability(self):
        """Test that Instrument is immutable (frozen=True)."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        with pytest.raises(AttributeError):
            inst.base = "ETH"  # type: ignore

    def test_str_representation(self):
        """Test __str__ representation."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
        )

        assert str(inst) == "BINANCEUSDM:BTC/USDT:PERPETUAL"

    def test_different_venues(self):
        """Test creating instruments for different venues."""
        bybit_inst = Instrument(
            venue=Venue.BYBIT,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.FUTURE,
        )

        assert str(bybit_inst) == "BYBIT:ETH/USDC:FUTURE"

    def test_different_instrument_types(self):
        """Test creating instruments with different types."""
        spot_inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="SOL",
            quote="USDT",
            symbol="SOLUSDT",
            code=3,
            instrument_type=InstrumentType.SPOT,
        )

        assert str(spot_inst) == "BINANCEUSDM:SOL/USDT:SPOT"


class TestInstrumentEdgeCases:
    """Test Instrument edge cases."""

    def test_empty_creation(self):
        """Test creating empty instrument."""
        inst = Instrument.empty()

        assert inst.venue == Venue.NULL
        assert inst.base == ""
        assert inst.quote == ""
        assert inst.symbol == ""
        assert inst.code == 0
        assert inst.instrument_type == InstrumentType.NULL

    def test_null_venue_handling(self):
        """Test instrument with NULL venue."""
        inst = Instrument(
            venue=Venue.NULL,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        assert inst.venue == Venue.NULL
        assert str(inst) == "NULL:BTC/USDT:PERPETUAL"

    def test_null_instrument_type_handling(self):
        """Test instrument with NULL instrument type."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.NULL,
        )

        assert inst.instrument_type == InstrumentType.NULL
        assert str(inst) == "BINANCEUSDM:BTC/USDT:NULL"

    def test_empty_symbol_string(self):
        """Test instrument with empty symbol string."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        assert inst.symbol == ""

    def test_zero_code(self):
        """Test instrument with code=0."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
        )

        assert inst.code == 0


class TestSimpleMap:
    """Test SimpleMap bidirectional mapping."""

    def test_initialization_empty(self):
        """Test creating empty SimpleMap."""
        smap = SimpleMap({})
        assert len(smap) == 0

    def test_initialization_with_data(self):
        """Test creating SimpleMap with initial data."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert len(smap) == 2

    def test_forward_access(self):
        """Test accessing value by key (forward direction)."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert smap["a"] == 1
        assert smap["b"] == 2

    def test_reverse_access(self):
        """Test accessing key by value (reverse direction)."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert smap[1] == "a"
        assert smap[2] == "b"

    def test_setitem_bidirectional(self):
        """Test setting item creates bidirectional mapping."""
        smap: SimpleMap[str, int] = SimpleMap({})
        smap["x"] = 10

        assert smap["x"] == 10
        assert smap[10] == "x"
        assert len(smap) == 1

    def test_contains_forward(self):
        """Test __contains__ for forward direction."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert "a" in smap
        assert "b" in smap
        assert "c" not in smap

    def test_contains_reverse(self):
        """Test __contains__ for reverse direction."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert 1 in smap
        assert 2 in smap
        assert 3 not in smap

    def test_get_with_existing_key(self):
        """Test get() method with existing key."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert smap.get("a") == 1
        assert smap.get(1) == "a"

    def test_get_with_missing_key_returns_none(self):
        """Test get() method with missing key returns None."""
        smap = SimpleMap({"a": 1})
        assert smap.get("missing") is None
        assert smap.get(999) is None

    def test_with_instrument_mapping(self):
        """Test SimpleMap with Instrument objects (real-world usage)."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.FUTURE,
        )

        imap: SimpleMap[str, Instrument] = SimpleMap({})
        imap[inst1.symbol] = inst1
        imap[inst2.symbol] = inst2

        assert len(imap) == 2
        assert imap["BTCUSDT"] == inst1
        assert imap["ETHUSDC"] == inst2
        assert imap.get("BTCUSDT") == inst1


class TestSimpleMapEdgeCases:
    """Test SimpleMap edge cases."""

    def test_keyerror_on_missing_key_getitem(self):
        """Test __getitem__ raises KeyError for missing key."""
        smap = SimpleMap({"a": 1})

        with pytest.raises(KeyError, match="Key.*not found"):
            _ = smap["missing"]

    def test_keyerror_on_missing_key_delitem(self):
        """Test __delitem__ raises KeyError for missing key."""
        smap = SimpleMap({"a": 1})

        with pytest.raises(KeyError, match="Key.*not found"):
            del smap["missing"]

    # TODO: Add deletion tests once SimpleMap.__delitem__ properly maintains bidirectional consistency
    # Currently __delitem__ only deletes from one map, leaving orphaned entries in the other

    @pytest.mark.xfail(
        reason="SimpleMap.__delitem__ does not remove reverse mapping yet",
        strict=True,
    )
    def test_delitem_removes_reverse_mapping(self):
        """Test deleting by key removes reverse mapping."""
        smap = SimpleMap({"a": 1})
        del smap["a"]

        assert 1 not in smap

    def test_with_different_types_str_int(self):
        """Test SimpleMap with str -> int mapping."""
        smap: SimpleMap[str, int] = SimpleMap({"x": 100, "y": 200})
        assert smap["x"] == 100
        assert smap[100] == "x"

    def test_with_different_types_int_str(self):
        """Test SimpleMap with int -> str mapping."""
        smap: SimpleMap[int, str] = SimpleMap({1: "one", 2: "two"})
        assert smap[1] == "one"
        assert smap["one"] == 1

    # TODO: Add update tests once SimpleMap.__setitem__ properly cleans up old values
    # Currently __setitem__ doesn't remove old values from _v_to_k_map when updating

    @pytest.mark.xfail(
        reason="SimpleMap.__setitem__ does not remove prior reverse mapping yet",
        strict=True,
    )
    def test_setitem_updates_reverse_mapping(self):
        """Test updating key removes old reverse mapping."""
        smap: SimpleMap[str, int] = SimpleMap({"a": 1})
        smap["a"] = 2

        assert 1 not in smap
        assert smap[2] == "a"


# =============================================================================
# =============================================================================


class TestInstrumentCollection:
    """Test InstrumentCollection operations."""

    def test_initialization_empty(self):
        """Test creating empty collection."""
        collection = InstrumentCollection()
        assert len(collection) == 0
        assert collection.instruments == []
        assert collection.venues == set()

    def test_initialization_with_instruments(self):
        """Test creating collection with instruments."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.FUTURE,
        )

        collection = InstrumentCollection([inst1, inst2])

        assert len(collection) == 2
        assert inst1 in collection
        assert inst2 in collection

    def test_is_empty(self):
        """Test is_empty reflects collection state."""
        collection = InstrumentCollection()
        assert collection.is_empty()

        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection.add(inst)
        assert not collection.is_empty()

        collection.remove(inst)
        assert collection.is_empty()

    def test_add_normal(self):
        """Test adding instrument to collection."""
        collection = InstrumentCollection()
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection.add(inst)

        assert len(collection) == 1
        assert inst in collection

    def test_add_duplicate_does_nothing(self):
        """Test adding duplicate instrument doesn't increase size."""
        collection = InstrumentCollection()
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection.add(inst)
        collection.add(inst)

        assert len(collection) == 1

    def test_get_by_venue_and_symbol(self):
        """Test fast lookup by venue and symbol."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection = InstrumentCollection([inst])
        result = collection.get(Venue.BINANCE_USDM, "BTCUSDT")

        assert result == inst

    def test_get_missing_returns_none(self):
        """Test get() returns None for missing instrument."""
        collection = InstrumentCollection()
        result = collection.get(Venue.BINANCE_USDM, "BTCUSDT")

        assert result is None

    def test_get_by_venue(self):
        """Test getting all instruments for a venue."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="ETH",
            quote="USDT",
            symbol="ETHUSDT",
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst3 = Instrument(
            venue=Venue.BYBIT,
            base="SOL",
            quote="USDC",
            symbol="SOLUSDC",
            code=3,
            instrument_type=InstrumentType.FUTURE,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        binance_instruments = collection.get_by_venue(Venue.BINANCE_USDM)

        assert len(binance_instruments) == 2
        assert inst1 in binance_instruments
        assert inst2 in binance_instruments
        assert inst3 not in binance_instruments

    def test_remove_existing(self):
        """Test removing instrument from collection."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection = InstrumentCollection([inst])
        collection.remove(inst)

        assert len(collection) == 0
        assert inst not in collection

    def test_remove_nonexistent_does_nothing(self):
        """Test removing non-existent instrument does nothing."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection = InstrumentCollection()
        collection.remove(inst)  # Should not raise

        assert len(collection) == 0

    def test_merge(self):
        """Test merging two collections."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.FUTURE,
        )

        collection1 = InstrumentCollection([inst1])
        collection2 = InstrumentCollection([inst2])

        collection1.merge(collection2)

        assert len(collection1) == 2
        assert inst1 in collection1
        assert inst2 in collection1

    def test_merge_with_duplicates(self):
        """Test merging collections with duplicate instruments."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection1 = InstrumentCollection([inst])
        collection2 = InstrumentCollection([inst])

        collection1.merge(collection2)

        assert len(collection1) == 1  # Duplicate not added


class TestInstrumentCollectionFiltering:
    """Test InstrumentCollection filtering comprehensively."""

    def test_filter_by_venues(self):
        """Test filtering by venue list."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.FUTURE,
        )
        inst3 = Instrument(
            venue=Venue.OKX,
            base="SOL",
            quote="USDT",
            symbol="SOLUSDT",
            code=3,
            instrument_type=InstrumentType.SPOT,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(venues=[Venue.BINANCE_USDM, Venue.BYBIT])

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_by_bases(self):
        """Test filtering by base asset list."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="ETH",
            quote="USDT",
            symbol="ETHUSDT",
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="SOL",
            quote="USDT",
            symbol="SOLUSDT",
            code=3,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(bases=["BTC", "ETH"])

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_by_quotes(self):
        """Test filtering by quote asset list."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.FUTURE,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="SOL",
            quote="BTC",
            symbol="SOLBTC",
            code=3,
            instrument_type=InstrumentType.SPOT,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(quotes=["USDT", "USDC"])

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_by_instrument_types(self):
        """Test filtering by instrument type list."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.FUTURE,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="SOL",
            quote="USDT",
            symbol="SOLUSDT",
            code=3,
            instrument_type=InstrumentType.SPOT,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(
            instrument_types=[InstrumentType.PERPETUAL, InstrumentType.FUTURE]
        )

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_by_base_blacklist(self):
        """Test filtering by base blacklist."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="ETH",
            quote="USDT",
            symbol="ETHUSDT",
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="DOGE",
            quote="USDT",
            symbol="DOGEUSDT",
            code=3,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(base_blacklist=["DOGE"])

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_by_quote_blacklist(self):
        """Test filtering by quote blacklist."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="SOL",
            quote="BTC",
            symbol="SOLBTC",
            code=3,
            instrument_type=InstrumentType.SPOT,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(quote_blacklist=["BTC"])

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_combined_filters(self):
        """Test filtering with multiple criteria simultaneously."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="ETH",
            quote="USDT",
            symbol="ETHUSDT",
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst3 = Instrument(
            venue=Venue.BYBIT,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=3,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst4 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="SOL",
            quote="USDT",
            symbol="SOLUSDT",
            code=4,
            instrument_type=InstrumentType.SPOT,
        )

        collection = InstrumentCollection([inst1, inst2, inst3, inst4])

        # Filter: Binance USDM, quote=USDT, type=PERPETUAL, base not SOL
        result = collection.filter(
            venues=[Venue.BINANCE_USDM],
            quotes=["USDT"],
            instrument_types=[InstrumentType.PERPETUAL],
            base_blacklist=["SOL"],
        )

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result  # Wrong venue
        assert inst4 not in result  # Wrong type

    def test_filter_no_criteria_returns_all(self):
        """Test filter with no criteria returns all instruments."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.FUTURE,
        )

        collection = InstrumentCollection([inst1, inst2])
        result = collection.filter()

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result


class TestInstrumentCollectionEdgeCases:
    """Test InstrumentCollection edge cases."""

    def test_iter(self):
        """Test __iter__ method."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.FUTURE,
        )

        collection = InstrumentCollection([inst1, inst2])
        instruments = list(collection)

        assert len(instruments) == 2
        assert inst1 in instruments
        assert inst2 in instruments

    def test_len(self):
        """Test __len__ method."""
        collection = InstrumentCollection()
        assert len(collection) == 0

        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection.add(inst)
        assert len(collection) == 1

    def test_contains(self):
        """Test __contains__ method."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.FUTURE,
        )

        collection = InstrumentCollection([inst1])

        assert inst1 in collection
        assert inst2 not in collection

    def test_instruments_property(self):
        """Test instruments property returns list."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection = InstrumentCollection([inst1])
        instruments = collection.instruments

        assert isinstance(instruments, list)
        assert len(instruments) == 1
        assert inst1 in instruments

    def test_venues_property(self):
        """Test venues property returns set."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="ETH",
            quote="USDT",
            symbol="ETHUSDT",
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
        )
        inst3 = Instrument(
            venue=Venue.BYBIT,
            base="SOL",
            quote="USDC",
            symbol="SOLUSDC",
            code=3,
            instrument_type=InstrumentType.FUTURE,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        venues = collection.venues

        assert isinstance(venues, set)
        assert len(venues) == 2
        assert Venue.BINANCE_USDM in venues
        assert Venue.BYBIT in venues

    def test_get_by_venue_empty_venue(self):
        """Test get_by_venue for venue with no instruments."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection = InstrumentCollection([inst])
        result = collection.get_by_venue(Venue.BYBIT)

        assert result == []

    def test_filter_returns_empty_when_no_match(self):
        """Test filter returns empty list when no instruments match."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
        )

        collection = InstrumentCollection([inst])
        result = collection.filter(venues=[Venue.BYBIT])

        assert result == []

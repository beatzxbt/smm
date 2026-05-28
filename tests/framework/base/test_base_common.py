"""Tests for framework.base.common module.

Tests cover:
- Venue enum (exchange identifiers)
- InstrumentType enum (instrument classifications)
- Instrument struct validation and operations
- InstrumentCollection filtering and grouping

Tests are organized by dependency layer:
1. Primitives: Venue, InstrumentType, Instrument
2. Composites: InstrumentCollection
"""

from __future__ import annotations

import pytest

from framework.base.common import (
    Asset,
    ClientOrderId,
    Instrument,
    InstrumentCollection,
    InstrumentType,
    OrderId,
    Symbol,
    Venue,
)


class TestVenue:
    """Test Venue enum."""

    def test_enum_values_exist(self):
        """Test all expected venue values exist."""
        assert Venue.NULL == "Null"
        assert Venue.BINANCE_USDM == "BinanceUsdM"
        assert Venue.BINANCE_COINM == "BinanceCoinM"
        assert Venue.BYBIT == "Bybit"
        assert Venue.OKX == "Okx"
        assert Venue.ZERO_ONE == "01"
        assert Venue.DECIBEL == "Decibel"
        assert Venue.HOTSTUFF == "Hotstuff"


class TestInstrumentType:
    """Test InstrumentType enum."""

    def test_enum_values_exist(self):
        """Test all expected instrument type values exist."""
        assert InstrumentType.NULL == "NULL"
        assert InstrumentType.SPOT == "Spot"
        assert InstrumentType.PERPETUAL == "Perpetual"


class TestOrderIdentifiers:
    """Test typed order identifier aliases."""

    def test_order_id_constructor_returns_string_value(self):
        """Test OrderId preserves the provided string value."""
        order_id = OrderId("order-123")
        assert order_id == "order-123"
        assert isinstance(order_id, str)

    def test_client_order_id_constructor_returns_string_value(self):
        """Test ClientOrderId preserves the provided string value."""
        client_order_id = ClientOrderId("client-abc")
        assert client_order_id == "client-abc"
        assert isinstance(client_order_id, str)


class TestInstrument:
    """Test Instrument struct creation and basic operations."""

    def test_creation_with_valid_data(self):
        """Test creating instrument with valid data."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        assert inst.venue == Venue.BINANCE_USDM
        assert inst.base == "BTC"
        assert inst.quote == "USDT"
        assert inst.symbol == "BTCUSDT"
        assert inst.code == 1
        assert inst.instrument_type == InstrumentType.PERPETUAL
        assert inst.tick_size == 0.01
        assert inst.lot_size == 0.001

    def test_frozen_immutability(self):
        """Test that Instrument is immutable (frozen=True)."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        with pytest.raises(AttributeError):
            inst.base = "ETH"  # type: ignore

    def test_str_representation(self):
        """Test __str__ representation."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        assert str(inst) == "BINANCEUSDM:BTC/USDT:PERPETUAL"

    def test_different_venues(self):
        """Test creating instruments for different venues."""
        bybit_inst = Instrument(
            venue=Venue.BYBIT,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        assert str(bybit_inst) == "BYBIT:ETH/USDC:PERPETUAL"

    def test_different_instrument_types(self):
        """Test creating instruments with different types."""
        spot_inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("SOL"),
            quote=Asset("USDT"),
            symbol=Symbol("SOLUSDT"),
            code=3,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.01,
            lot_size=0.001,
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
        assert inst.tick_size == 0.0
        assert inst.lot_size == 0.0

    def test_empty_with_overrides(self):
        """Test creating a blank instrument with selected overrides."""
        inst = Instrument.empty_with(venue=Venue.BYBIT)

        assert inst.venue == Venue.BYBIT
        assert inst.base == ""
        assert inst.quote == ""
        assert inst.symbol == ""
        assert inst.code == 0
        assert inst.instrument_type == InstrumentType.NULL
        assert inst.tick_size == 0.0
        assert inst.lot_size == 0.0

    def test_null_venue_handling(self):
        """Test instrument with NULL venue."""
        inst = Instrument(
            venue=Venue.NULL,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        assert inst.venue == Venue.NULL
        assert str(inst) == "NULL:BTC/USDT:PERPETUAL"

    def test_null_instrument_type_handling(self):
        """Test invalid generic instrument payload raises ValueError."""
        with pytest.raises(
            ValueError, match="symbol must be empty when instrument_type is NULL"
        ):
            Instrument(
                venue=Venue.BINANCE_USDM,
                base=Asset("BTC"),
                quote=Asset("USDT"),
                symbol=Symbol("BTCUSDT"),
                code=1,
                instrument_type=InstrumentType.NULL,
                tick_size=0.01,
                lot_size=0.001,
            )

    def test_empty_symbol_string(self):
        """Test missing symbol for non-NULL instrument raises ValueError."""
        with pytest.raises(
            ValueError, match="symbol must be non-empty for non-NULL instruments"
        ):
            Instrument(
                venue=Venue.BINANCE_USDM,
                base=Asset("BTC"),
                quote=Asset("USDT"),
                symbol=Symbol(""),
                code=1,
                instrument_type=InstrumentType.PERPETUAL,
                tick_size=0.01,
                lot_size=0.001,
            )

    def test_base_must_be_present_in_symbol(self):
        """Test non-NULL instruments enforce base presence in symbol."""
        with pytest.raises(
            ValueError, match="base must be present in symbol for non-NULL instruments"
        ):
            Instrument(
                venue=Venue.BINANCE_USDM,
                base=Asset("ETH"),
                quote=Asset("USDT"),
                symbol=Symbol("BTCUSDT"),
                code=1,
                instrument_type=InstrumentType.PERPETUAL,
                tick_size=0.01,
                lot_size=0.001,
            )

    def test_quote_must_be_present_in_symbol(self):
        """Test non-NULL instruments enforce quote presence in symbol."""
        with pytest.raises(
            ValueError,
            match="quote must be present in symbol for non-NULL instruments",
        ):
            Instrument(
                venue=Venue.BINANCE_USDM,
                base=Asset("BTC"),
                quote=Asset("USDC"),
                symbol=Symbol("BTCUSDT"),
                code=1,
                instrument_type=InstrumentType.PERPETUAL,
                tick_size=0.01,
                lot_size=0.001,
            )

    def test_empty_base_rejected_for_non_null_instrument(self):
        """Test empty base is rejected for non-NULL instruments."""
        with pytest.raises(
            ValueError, match="base must be present in symbol for non-NULL instruments"
        ):
            Instrument(
                venue=Venue.BINANCE_USDM,
                base=Asset(""),
                quote=Asset("USDT"),
                symbol=Symbol("BTCUSDT"),
                code=1,
                instrument_type=InstrumentType.PERPETUAL,
                tick_size=0.01,
                lot_size=0.001,
            )

    def test_empty_quote_rejected_for_non_null_instrument(self):
        """Test empty quote is rejected for non-NULL instruments."""
        with pytest.raises(
            ValueError,
            match="quote must be present in symbol for non-NULL instruments",
        ):
            Instrument(
                venue=Venue.BINANCE_USDM,
                base=Asset("BTC"),
                quote=Asset(""),
                symbol=Symbol("BTCUSDT"),
                code=1,
                instrument_type=InstrumentType.PERPETUAL,
                tick_size=0.01,
                lot_size=0.001,
            )

    def test_tick_size_must_be_positive_for_non_null_instrument(self):
        """Test non-positive tick size raises ValueError."""
        with pytest.raises(
            ValueError, match="tick_size must be > 0 for non-NULL instruments"
        ):
            Instrument(
                venue=Venue.BINANCE_USDM,
                base=Asset("BTC"),
                quote=Asset("USDT"),
                symbol=Symbol("BTCUSDT"),
                code=1,
                instrument_type=InstrumentType.PERPETUAL,
                tick_size=0.0,
                lot_size=0.001,
            )

    def test_lot_size_must_be_positive_for_non_null_instrument(self):
        """Test non-positive lot size raises ValueError."""
        with pytest.raises(
            ValueError, match="lot_size must be > 0 for non-NULL instruments"
        ):
            Instrument(
                venue=Venue.BINANCE_USDM,
                base=Asset("BTC"),
                quote=Asset("USDT"),
                symbol=Symbol("BTCUSDT"),
                code=1,
                instrument_type=InstrumentType.PERPETUAL,
                tick_size=0.01,
                lot_size=0.0,
            )

    def test_null_instrument_type_rejects_non_empty_base(self):
        """Test generic instrument payload rejects non-empty base."""
        with pytest.raises(
            ValueError, match="base must be empty when instrument_type is NULL"
        ):
            Instrument(
                venue=Venue.BINANCE_USDM,
                base=Asset("BTC"),
                quote=Asset(""),
                symbol=Symbol(""),
                code=1,
                instrument_type=InstrumentType.NULL,
                tick_size=0.0,
                lot_size=0.0,
            )

    def test_null_instrument_type_rejects_non_empty_quote(self):
        """Test generic instrument payload rejects non-empty quote."""
        with pytest.raises(
            ValueError, match="quote must be empty when instrument_type is NULL"
        ):
            Instrument(
                venue=Venue.BINANCE_USDM,
                base=Asset(""),
                quote=Asset("USDT"),
                symbol=Symbol(""),
                code=1,
                instrument_type=InstrumentType.NULL,
                tick_size=0.0,
                lot_size=0.0,
            )

    def test_empty_with_repeated_call_value_equivalence(self):
        """Test repeated empty_with calls return equivalent values."""
        first = Instrument.empty_with(venue=Venue.BYBIT, code=7)
        second = Instrument.empty_with(venue=Venue.BYBIT, code=7)

        assert first == second
        assert first.venue == Venue.BYBIT
        assert first.code == 7

    def test_zero_code(self):
        """Test instrument with code=0."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        assert inst.code == 0


class TestInstrumentCollection:
    """Test InstrumentCollection operations."""

    def test_initialization_empty(self):
        """Test creating empty collection."""
        collection = InstrumentCollection([])
        assert len(collection) == 0
        assert collection.instruments == []
        assert collection.venue is None

    def test_initialization_with_instruments(self):
        """Test creating collection with instruments."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2])

        assert len(collection) == 2
        assert inst1 in collection
        assert inst2 in collection

    def test_initialization_single_instrument(self):
        """Test creating collection with a single instrument."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst])

        assert len(collection) == 1
        assert inst in collection

    def test_initialization_deduplicates(self):
        """Test duplicate instruments are deduplicated at initialization."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst, inst])

        assert len(collection) == 1

    def test_initialization_duplicate_symbol_conflict_raises(self):
        """Test same symbol with different payload is rejected."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        with pytest.raises(ValueError, match="duplicate symbol"):
            InstrumentCollection([inst1, inst2])

    def test_get_by_symbol(self):
        """Test fast lookup by symbol for single-venue collections."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst])
        result = collection.get(Symbol("BTCUSDT"))

        assert result == inst

    def test_get_missing_returns_none(self):
        """Test get() returns None for missing instrument."""
        collection = InstrumentCollection([])
        result = collection.get(Symbol("BTCUSDT"))

        assert result is None

    def test_initialization_multi_venue_raises(self):
        """Test collection creation fails when venues are mixed."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        with pytest.raises(ValueError, match="single venue only"):
            InstrumentCollection([inst1, inst2])

    def test_venue_property(self):
        """Test venue property for non-empty collections."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDT"),
            symbol=Symbol("ETHUSDT"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("SOL"),
            quote=Asset("USDC"),
            symbol=Symbol("SOLUSDC"),
            code=3,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        assert collection.venue == Venue.BINANCE_USDM


class TestInstrumentCollectionFiltering:
    """Test InstrumentCollection filtering comprehensively."""

    def test_filter_with_type_criteria(self):
        """Test filtering by instrument type criteria."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("SOL"),
            quote=Asset("USDT"),
            symbol=Symbol("SOLUSDT"),
            code=3,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(
            instrument_types=[
                InstrumentType.PERPETUAL,
                InstrumentType.PERPETUAL,
                InstrumentType.SPOT,
            ]
        )

        assert len(result) == 3
        assert inst1 in result
        assert inst2 in result
        assert inst3 in result

    def test_filter_by_bases(self):
        """Test filtering by base asset list."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDT"),
            symbol=Symbol("ETHUSDT"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("SOL"),
            quote=Asset("USDT"),
            symbol=Symbol("SOLUSDT"),
            code=3,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(bases=[Asset("BTC"), Asset("ETH")])

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_by_quotes(self):
        """Test filtering by quote asset list."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("SOL"),
            quote=Asset("BTC"),
            symbol=Symbol("SOLBTC"),
            code=3,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(quotes=[Asset("USDT"), Asset("USDC")])

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_by_instrument_types(self):
        """Test filtering by instrument type list."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("SOL"),
            quote=Asset("USDT"),
            symbol=Symbol("SOLUSDT"),
            code=3,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(
            instrument_types=[InstrumentType.PERPETUAL, InstrumentType.PERPETUAL]
        )

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_by_base_blacklist(self):
        """Test filtering by base blacklist."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDT"),
            symbol=Symbol("ETHUSDT"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("DOGE"),
            quote=Asset("USDT"),
            symbol=Symbol("DOGEUSDT"),
            code=3,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(base_blacklist=[Asset("DOGE")])

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_by_quote_blacklist(self):
        """Test filtering by quote blacklist."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("SOL"),
            quote=Asset("BTC"),
            symbol=Symbol("SOLBTC"),
            code=3,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        result = collection.filter(quote_blacklist=[Asset("BTC")])

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result

    def test_filter_combined_filters(self):
        """Test filtering with multiple criteria simultaneously."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDT"),
            symbol=Symbol("ETHUSDT"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDC"),
            symbol=Symbol("BTCUSDC"),
            code=3,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst4 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("SOL"),
            quote=Asset("USDT"),
            symbol=Symbol("SOLUSDT"),
            code=4,
            instrument_type=InstrumentType.SPOT,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2, inst3, inst4])

        # Filter: quote=USDT, type=PERPETUAL, base not SOL
        result = collection.filter(
            quotes=[Asset("USDT")],
            instrument_types=[InstrumentType.PERPETUAL],
            base_blacklist=[Asset("SOL")],
        )

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result
        assert inst3 not in result  # Wrong quote
        assert inst4 not in result  # Wrong type

    def test_filter_no_criteria_returns_all(self):
        """Test filter with no criteria returns all instruments."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2])
        result = collection.filter()

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result

    def test_filter_blacklist_takes_precedence_over_whitelist(self):
        """Test blacklist exclusion wins when also explicitly whitelisted."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDT"),
            symbol=Symbol("ETHUSDT"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2])
        result = collection.filter(
            bases=[Asset("BTC"), Asset("ETH")], base_blacklist=[Asset("BTC")]
        )

        assert inst1 not in result
        assert inst2 in result

    def test_filter_with_empty_iterables_behaves_like_no_filter(self):
        """Test empty filter iterables do not exclude instruments."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2])
        result = collection.filter(bases=[], quotes=[], instrument_types=[])

        assert len(result) == 2
        assert inst1 in result
        assert inst2 in result


class TestInstrumentCollectionEdgeCases:
    """Test InstrumentCollection edge cases."""

    def test_iter(self):
        """Test __iter__ method."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2])
        instruments = list(collection)

        assert len(instruments) == 2
        assert inst1 in instruments
        assert inst2 in instruments

    def test_len(self):
        """Test __len__ method."""
        collection = InstrumentCollection([])
        assert len(collection) == 0

        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection_with_one = InstrumentCollection([inst])
        assert len(collection_with_one) == 1

    def test_contains(self):
        """Test __contains__ method."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BYBIT,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1])

        assert inst1 in collection
        assert inst2 not in collection

    def test_instruments_property(self):
        """Test instruments property returns list."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1])
        instruments = collection.instruments

        assert isinstance(instruments, list)
        assert len(instruments) == 1
        assert inst1 in instruments

    def test_instruments_property_returns_copy(self):
        """Test mutating returned list does not affect collection state."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDC"),
            symbol=Symbol("ETHUSDC"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2])
        instruments = collection.instruments
        instruments.clear()

        assert len(instruments) == 0
        assert len(collection) == 2
        assert collection.instruments == [inst1, inst2]

    def test_venue_property_edge_case(self):
        """Test venue property returns the single collection venue."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("ETH"),
            quote=Asset("USDT"),
            symbol=Symbol("ETHUSDT"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst3 = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("SOL"),
            quote=Asset("USDC"),
            symbol=Symbol("SOLUSDC"),
            code=3,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst1, inst2, inst3])
        assert collection.venue == Venue.BINANCE_USDM

    def test_filter_returns_empty_when_no_match(self):
        """Test filter returns empty list when no instruments match."""
        inst = Instrument(
            venue=Venue.BINANCE_USDM,
            base=Asset("BTC"),
            quote=Asset("USDT"),
            symbol=Symbol("BTCUSDT"),
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        collection = InstrumentCollection([inst])
        result = collection.filter(bases=[Asset("ETH")])

        assert result == []

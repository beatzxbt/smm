"""Tests for framework.base.tools.map module.

Tests cover:
- EnumMap bidirectional enum<->string conversion
- SimpleMap bidirectional key<->value lookups
- Default value and error handling behavior

Tests are organized by dependency layer:
1. Primitives: EnumMap, SimpleMap
2. Composite examples: SimpleMap with Instrument values
"""

from __future__ import annotations

import pytest

from framework.base.common import Instrument, InstrumentType, Venue
from framework.base.stream.models import OrderTimeInForce
from framework.base.tools.map import EnumMap, SimpleMap


class TestEnumMap:
    """Test EnumMap bidirectional enum<->string mapping."""

    @pytest.fixture
    def tif_map(self):
        """Create a reusable EnumMap for time-in-force values."""
        return EnumMap(
            enum_class=OrderTimeInForce,
            mapping={
                OrderTimeInForce.GTC: "GTC",
                OrderTimeInForce.IOC: "IOC",
                OrderTimeInForce.FOK: "FOK",
                OrderTimeInForce.PO: "PostOnly",
            },
        )

    def test_enum_to_str_all_values(self, tif_map):
        """Test converting all enum values to strings."""
        assert tif_map.enum_to_str(OrderTimeInForce.GTC) == "GTC"
        assert tif_map.enum_to_str(OrderTimeInForce.IOC) == "IOC"
        assert tif_map.enum_to_str(OrderTimeInForce.FOK) == "FOK"
        assert tif_map.enum_to_str(OrderTimeInForce.PO) == "PostOnly"

    def test_str_to_enum_all_values(self, tif_map):
        """Test converting all strings to enum values."""
        assert tif_map.str_to_enum("GTC") == OrderTimeInForce.GTC
        assert tif_map.str_to_enum("IOC") == OrderTimeInForce.IOC
        assert tif_map.str_to_enum("FOK") == OrderTimeInForce.FOK
        assert tif_map.str_to_enum("PostOnly") == OrderTimeInForce.PO

    def test_bidirectional_consistency(self, tif_map):
        """Test enum->str->enum round trip consistency."""
        for enum_val in [OrderTimeInForce.GTC, OrderTimeInForce.IOC]:
            str_val = tif_map.enum_to_str(enum_val)
            assert tif_map.str_to_enum(str_val) == enum_val


class TestEnumMapEdgeCases:
    """Test EnumMap edge cases and error handling."""

    def test_str_to_enum_with_default(self):
        """Test str_to_enum returns default for unknown string."""
        tif_map = EnumMap(
            enum_class=OrderTimeInForce,
            mapping={
                OrderTimeInForce.GTC: "GTC",
                OrderTimeInForce.IOC: "IOC",
            },
        )

        result = tif_map.str_to_enum("UNKNOWN", default=OrderTimeInForce.GTC)
        assert result == OrderTimeInForce.GTC

    def test_str_to_enum_missing_no_default_raises(self):
        """Test str_to_enum raises KeyError for unknown string."""
        tif_map = EnumMap(
            enum_class=OrderTimeInForce,
            mapping={
                OrderTimeInForce.GTC: "GTC",
                OrderTimeInForce.IOC: "IOC",
            },
        )

        with pytest.raises(KeyError, match="Unknown string value.*UNKNOWN"):
            tif_map.str_to_enum("UNKNOWN")

    def test_enum_to_str_missing_raises(self):
        """Test enum_to_str raises KeyError for unmapped enum value."""
        tif_map = EnumMap(
            enum_class=OrderTimeInForce,
            mapping={
                OrderTimeInForce.GTC: "GTC",
            },
        )

        with pytest.raises(KeyError):
            tif_map.enum_to_str(OrderTimeInForce.IOC)


class TestSimpleMap:
    """Test SimpleMap bidirectional mapping behavior."""

    def test_initialization_empty(self):
        """Test creating an empty SimpleMap."""
        smap = SimpleMap({})
        assert len(smap) == 0

    def test_initialization_with_data(self):
        """Test creating a SimpleMap with initial values."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert len(smap) == 2

    def test_forward_access(self):
        """Test accessing value by key."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert smap["a"] == 1
        assert smap["b"] == 2

    def test_reverse_access(self):
        """Test accessing key by value."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert smap[1] == "a"
        assert smap[2] == "b"

    def test_setitem_bidirectional(self):
        """Test setting item creates forward and reverse mappings."""
        smap: SimpleMap[str, int] = SimpleMap({})
        smap["x"] = 10

        assert smap["x"] == 10
        assert smap[10] == "x"
        assert len(smap) == 1

    def test_contains_forward(self):
        """Test __contains__ for key side."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert "a" in smap
        assert "b" in smap
        assert "c" not in smap

    def test_contains_reverse(self):
        """Test __contains__ for value side."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert 1 in smap
        assert 2 in smap
        assert 3 not in smap

    def test_get_with_existing_key(self):
        """Test get() resolves keys from either side."""
        smap = SimpleMap({"a": 1, "b": 2})
        assert smap.get("a") == 1
        assert smap.get(1) == "a"

    def test_get_with_missing_key_returns_none(self):
        """Test get() returns None for unknown key/value."""
        smap = SimpleMap({"a": 1})
        assert smap.get("missing") is None
        assert smap.get(999) is None

    def test_get_none_returns_none(self):
        """Test get() handles None gracefully when absent."""
        smap = SimpleMap({})
        assert smap.get(None) is None

    def test_with_instrument_mapping(self):
        """Test SimpleMap with Instrument objects."""
        inst1 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="BTC",
            quote="USDT",
            symbol="BTCUSDT",
            code=1,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        inst2 = Instrument(
            venue=Venue.BINANCE_USDM,
            base="ETH",
            quote="USDC",
            symbol="ETHUSDC",
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        imap: SimpleMap[str, Instrument] = SimpleMap({})
        imap[inst1.symbol] = inst1
        imap[inst2.symbol] = inst2

        assert len(imap) == 2
        assert imap["BTCUSDT"] == inst1
        assert imap["ETHUSDC"] == inst2
        assert imap.get("BTCUSDT") == inst1
        assert imap.get(inst1) == "BTCUSDT"

    def test_multiple_instruments(self):
        """Test inserting and retrieving multiple instrument pairs."""
        smap: SimpleMap[str, Instrument] = SimpleMap({})

        instruments = [
            Instrument(
                venue=Venue.BYBIT,
                symbol="BTCUSDT",
                base="BTC",
                quote="USDT",
                code=0,
                instrument_type=InstrumentType.PERPETUAL,
                tick_size=0.01,
                lot_size=0.001,
            ),
            Instrument(
                venue=Venue.BYBIT,
                symbol="ETHUSDT",
                base="ETH",
                quote="USDT",
                code=0,
                instrument_type=InstrumentType.PERPETUAL,
                tick_size=0.01,
                lot_size=0.001,
            ),
            Instrument(
                venue=Venue.BYBIT,
                symbol="SOLUSDT",
                base="SOL",
                quote="USDT",
                code=0,
                instrument_type=InstrumentType.PERPETUAL,
                tick_size=0.01,
                lot_size=0.001,
            ),
        ]

        for inst in instruments:
            smap[inst.symbol] = inst

        assert smap.get("BTCUSDT") == instruments[0]
        assert smap.get("ETHUSDT") == instruments[1]
        assert smap.get("SOLUSDT") == instruments[2]
        assert smap.get(instruments[0]) == "BTCUSDT"
        assert smap.get(instruments[1]) == "ETHUSDT"

    def test_symbol_case_handling(self):
        """Test map treats case-different keys as distinct."""
        smap: SimpleMap[str, Instrument] = SimpleMap({})

        btc_binance = Instrument(
            venue=Venue.BINANCE_USDM,
            symbol="btcusdt",
            base="btc",
            quote="usdt",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        btc_bybit = Instrument(
            venue=Venue.BYBIT,
            symbol="BTCUSDT",
            base="BTC",
            quote="USDT",
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )

        smap["btcusdt"] = btc_binance
        smap["BTCUSDT"] = btc_bybit

        assert smap.get("btcusdt") == btc_binance
        assert smap.get("BTCUSDT") == btc_bybit
        assert smap.get(btc_binance) == "btcusdt"
        assert smap.get(btc_bybit) == "BTCUSDT"


class TestSimpleMapEdgeCases:
    """Test SimpleMap edge cases."""

    def test_keyerror_on_missing_key_getitem(self):
        """Test __getitem__ raises KeyError for unknown key."""
        smap = SimpleMap({"a": 1})
        with pytest.raises(KeyError, match="Key.*not found"):
            _ = smap["missing"]

    def test_keyerror_on_missing_key_delitem(self):
        """Test __delitem__ raises KeyError for unknown key."""
        smap = SimpleMap({"a": 1})
        with pytest.raises(KeyError, match="Key.*not found"):
            del smap["missing"]

    def test_delitem_removes_reverse_mapping(self):
        """Test deleting key removes paired reverse entry."""
        smap = SimpleMap({"a": 1})
        del smap["a"]

        assert 1 not in smap
        assert "a" not in smap
        assert len(smap) == 0

    def test_delitem_by_value_removes_forward_mapping(self):
        """Test deleting value removes paired forward entry."""
        smap: SimpleMap[str, int] = SimpleMap({"a": 1, "b": 2})
        del smap[1]

        assert "a" not in smap
        assert 1 not in smap
        assert "b" in smap
        assert 2 in smap
        assert len(smap) == 1

    def test_with_different_types_str_int(self):
        """Test mapping with str keys and int values."""
        smap: SimpleMap[str, int] = SimpleMap({"x": 100, "y": 200})
        assert smap["x"] == 100
        assert smap[100] == "x"

    def test_with_different_types_int_str(self):
        """Test mapping with int keys and str values."""
        smap: SimpleMap[int, str] = SimpleMap({1: "one", 2: "two"})
        assert smap[1] == "one"
        assert smap["one"] == 1

    def test_setitem_updates_reverse_mapping(self):
        """Test updating key removes old reverse association."""
        smap: SimpleMap[str, int] = SimpleMap({"a": 1})
        smap["a"] = 2

        assert 1 not in smap
        assert smap[2] == "a"
        assert len(smap) == 1

    def test_setitem_overwrites_existing_value(self):
        """Test setting used value rewires previous key association."""
        smap: SimpleMap[str, int] = SimpleMap({"a": 1, "b": 2})
        smap["c"] = 2

        assert "b" not in smap
        assert smap[2] == "c"
        assert smap["c"] == 2
        assert len(smap) == 2

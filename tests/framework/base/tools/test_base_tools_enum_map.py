"""Tests for framework.base.tools.enum_map module.

Tests cover:
- EnumMap bidirectional enum<->string conversion
- Default value handling
- Error handling for missing keys

Tests are organized by dependency layer:
1. Primitives: EnumMap basic operations and edge cases
"""

from __future__ import annotations

import pytest

from framework.base.stream.models import OrderTimeInForce
from framework.base.tools import EnumMap


class TestEnumMap:
    """Test EnumMap bidirectional enum<->string mapping."""

    @pytest.fixture
    def tif_map(self):
        """Reusable EnumMap for tests."""
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
        """Test that enum->str->enum round trip is consistent."""
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
        """Test str_to_enum raises KeyError for unknown string without default."""
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

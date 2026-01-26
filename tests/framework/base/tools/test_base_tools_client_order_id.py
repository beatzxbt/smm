"""Tests for framework.base.tools.client_order_id module.

Tests cover:
- ClientOrderId generation with various parameters
- Prefix/suffix handling
- Character type validation
- Length constraints

Tests are organized by dependency layer:
1. Primitives: AllowedOrderIdChars enum and ClientOrderId generation
"""

from __future__ import annotations

import pytest

from framework.base.tools.client_order_id import AllowedOrderIdChars, ClientOrderId
from mm_toolbox.time import time_ns


class TestAllowedOrderIdChars:
    """Test AllowedOrderIdChars enum."""

    def test_enum_values_exist(self):
        """Test all expected enum values exist."""
        assert AllowedOrderIdChars.NUMERIC == 0
        assert AllowedOrderIdChars.ALPHABETIC == 1
        assert AllowedOrderIdChars.ALPHANUMERIC == 2


class TestClientOrderIdGeneration:
    """Test ClientOrderId generation logic."""

    def test_generate_basic_default_length(self):
        """Test basic generation with default length."""
        expected_len = min(36, len(str(time_ns())))
        cloid = ClientOrderId.generate()

        assert isinstance(cloid, str)
        assert len(cloid) == expected_len  # Default length is a max
        assert cloid.isdigit()  # Should be all digits by default

    def test_generate_with_custom_length(self):
        """Test generation with custom length."""
        expected_len = min(20, len(str(time_ns())))
        cloid = ClientOrderId.generate(length=20)

        assert len(cloid) == expected_len
        assert cloid.isdigit()

    def test_generate_with_prefix(self):
        """Test generation with prefix."""
        expected_len = min(36, len("ABC") + len(str(time_ns())))
        cloid = ClientOrderId.generate(length=36, prefix="ABC")

        assert len(cloid) == expected_len
        assert cloid.startswith("ABC")

    def test_generate_with_suffix(self):
        """Test generation with suffix."""
        expected_len = min(36, len(str(time_ns())) + len("XYZ"))
        cloid = ClientOrderId.generate(length=36, suffix="XYZ")

        assert len(cloid) == expected_len
        assert cloid.endswith("XYZ")

    def test_generate_with_prefix_and_suffix(self):
        """Test generation with both prefix and suffix."""
        expected_len = min(36, len("A") + len(str(time_ns())) + len("Z"))
        cloid = ClientOrderId.generate(length=36, prefix="A", suffix="Z")

        assert len(cloid) == expected_len
        assert cloid.startswith("A")
        assert cloid.endswith("Z")

    def test_generate_uniqueness(self):
        """Test that consecutive generations produce unique IDs."""
        cloid1 = ClientOrderId.generate()
        cloid2 = ClientOrderId.generate()

        assert cloid1 != cloid2

    def test_callable_instance(self):
        """Test ClientOrderId instance is callable."""
        expected_len = min(36, len(str(time_ns())))
        gen = ClientOrderId()
        cloid = gen()

        assert isinstance(cloid, str)
        assert len(cloid) == expected_len


class TestClientOrderIdValidation:
    """Test ClientOrderId validation and constraints."""

    def test_zero_length_raises(self):
        """Test length must be > 0."""
        with pytest.raises(ValueError, match="Length must be >0"):
            ClientOrderId.generate(length=0)

    def test_negative_length_raises(self):
        """Test negative length raises."""
        with pytest.raises(ValueError, match="Length must be >0"):
            ClientOrderId.generate(length=-5)

    def test_prefix_suffix_too_long_raises(self):
        """Test prefix + suffix length must be less than total length."""
        with pytest.raises(
            ValueError, match="Prefix \\+ suffix length must be less than total length"
        ):
            ClientOrderId.generate(length=10, prefix="12345", suffix="67890")

    def test_numeric_with_string_prefix_raises(self):
        """Test NUMERIC mode rejects string prefix."""
        with pytest.raises(
            ValueError,
            match="Prefix and suffix must be integers if allowed_chars is NUMERIC",
        ):
            ClientOrderId.generate(
                prefix="ABC", allowed_chars=AllowedOrderIdChars.NUMERIC
            )

    def test_alphabetic_with_int_prefix_raises(self):
        """Test ALPHABETIC mode rejects integer prefix."""
        with pytest.raises(
            ValueError,
            match="Prefix and suffix must be strings if allowed_chars is ALPHABETIC",
        ):
            ClientOrderId.generate(
                prefix=123, allowed_chars=AllowedOrderIdChars.ALPHABETIC
            )

    def test_alphanumeric_accepts_mixed_types(self):
        """Test ALPHANUMERIC mode accepts both string and int prefix/suffix."""
        cloid1 = ClientOrderId.generate(
            prefix="A", suffix=1, allowed_chars=AllowedOrderIdChars.ALPHANUMERIC
        )
        cloid2 = ClientOrderId.generate(
            prefix=1, suffix="Z", allowed_chars=AllowedOrderIdChars.ALPHANUMERIC
        )

        assert cloid1.startswith("A")
        assert cloid1.endswith("1")
        assert cloid2.startswith("1")
        assert cloid2.endswith("Z")


class TestClientOrderIdEdgeCases:
    """Test ClientOrderId edge cases."""

    def test_minimal_length_with_prefix_suffix(self):
        """Test minimum viable length with prefix and suffix."""
        # Length 3: prefix(1) + time(1) + suffix(1)
        cloid = ClientOrderId.generate(length=3, prefix="A", suffix="Z")

        assert len(cloid) == 3
        assert cloid[0] == "A"
        assert cloid[2] == "Z"
        assert cloid[1].isdigit()  # Middle character should be from time_ns

    def test_time_truncation_for_short_length(self):
        """Test time_ns is truncated when available space is limited."""
        cloid = ClientOrderId.generate(length=10, prefix="ABC", suffix="XYZ")

        # Length 10: ABC(3) + time(4) + XYZ(3)
        assert len(cloid) == 10
        assert cloid.startswith("ABC")
        assert cloid.endswith("XYZ")
        # Middle 4 chars should be the last 4 digits of time_ns
        middle = cloid[3:7]
        assert middle.isdigit()
        assert len(middle) == 4

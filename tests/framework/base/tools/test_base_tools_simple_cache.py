"""Tests for framework.base.tools.simple_cache module.

Tests cover:
- SimpleCache sequence tracking with is_higher
- is_different and is_lower methods
- Cache operations (get, clear)
- Multiple key management

Tests are organized by dependency layer:
1. Primitives: SimpleCache basic operations and edge cases
"""

from __future__ import annotations

import pytest

from framework.base.tools import SimpleCache


# =============================================================================
# =============================================================================


class TestSimpleCache:
    """Test SimpleCache basic operations."""

    @pytest.fixture
    def cache(self):
        """Reusable empty cache for tests."""
        return SimpleCache()

    def test_is_higher_new_key(self, cache):
        """Test is_higher returns True for new keys."""
        assert cache.is_higher("BTCUSDT", 123) is True
        assert cache.get("BTCUSDT") == 123

    def test_is_higher_newer_value(self, cache):
        """Test is_higher returns True for strictly higher values."""
        cache.is_higher("BTCUSDT", 100)
        assert cache.is_higher("BTCUSDT", 200) is True
        assert cache.get("BTCUSDT") == 200

    def test_is_higher_equal_value(self, cache):
        """Test is_higher returns False for equal values."""
        cache.is_higher("BTCUSDT", 200)
        assert cache.is_higher("BTCUSDT", 200) is False
        assert cache.get("BTCUSDT") == 200

    def test_is_higher_older_value(self, cache):
        """Test is_higher returns False for lower values."""
        cache.is_higher("BTCUSDT", 200)
        assert cache.is_higher("BTCUSDT", 100) is False
        assert cache.get("BTCUSDT") == 200

    def test_is_different_new_key(self, cache):
        """Test is_different returns True for new keys."""
        assert cache.is_different("BTCUSDT", 123) is True
        assert cache.get("BTCUSDT") == 123

    def test_is_different_same_value(self, cache):
        """Test is_different returns False for same value."""
        cache.is_different("BTCUSDT", 100)
        assert cache.is_different("BTCUSDT", 100) is False
        assert cache.get("BTCUSDT") == 100

    def test_is_different_different_value(self, cache):
        """Test is_different returns True for different value."""
        cache.is_different("BTCUSDT", 100)
        # is_different doesn't update the cache when returning False
        assert cache.is_different("BTCUSDT", 200) is True

    def test_is_lower_new_key(self, cache):
        """Test is_lower returns True for new keys."""
        assert cache.is_lower("BTCUSDT", 123) is True
        assert cache.get("BTCUSDT") == 123

    def test_is_lower_lower_value(self, cache):
        """Test is_lower returns True for strictly lower values."""
        cache.is_lower("BTCUSDT", 200)
        assert cache.is_lower("BTCUSDT", 100) is True
        # Note: is_lower updates cache on first call but not when returning True
        assert cache.get("BTCUSDT") == 200

    def test_is_lower_equal_value(self, cache):
        """Test is_lower returns False for equal values."""
        cache.is_lower("BTCUSDT", 200)
        assert cache.is_lower("BTCUSDT", 200) is False

    def test_is_lower_higher_value(self, cache):
        """Test is_lower returns False for higher values."""
        cache.is_lower("BTCUSDT", 100)
        assert cache.is_lower("BTCUSDT", 200) is False

    def test_get_existing_key(self, cache):
        """Test get returns cached value for existing key."""
        cache.is_higher("BTCUSDT", 100)
        assert cache.get("BTCUSDT") == 100

    def test_get_nonexistent_key(self, cache):
        """Test get returns None for nonexistent keys."""
        assert cache.get("NONEXISTENT") is None

    def test_multiple_keys_independent(self, cache):
        """Test cache manages multiple keys independently."""
        cache.is_higher("BTCUSDT", 100)
        cache.is_higher("ETHUSDT", 200)
        cache.is_higher("SOLUSDT", 300)

        assert cache.get("BTCUSDT") == 100
        assert cache.get("ETHUSDT") == 200
        assert cache.get("SOLUSDT") == 300

        # Updating one key doesn't affect others
        cache.is_higher("BTCUSDT", 150)
        assert cache.get("BTCUSDT") == 150
        assert cache.get("ETHUSDT") == 200


class TestSimpleCacheEdgeCases:
    """Test SimpleCache edge cases and complex scenarios."""

    def test_clear_removes_all_entries(self):
        """Test clearing the cache removes all entries."""
        cache = SimpleCache()
        cache.is_higher("BTCUSDT", 100)
        cache.is_higher("ETHUSDT", 200)

        cache.clear()

        assert cache.get("BTCUSDT") is None
        assert cache.get("ETHUSDT") is None

    def test_deduplication_use_case(self):
        """Test realistic trade deduplication scenario."""
        cache = SimpleCache()

        # Simulate receiving trades with ascending sequence IDs
        assert cache.is_higher("BTCUSDT", 1) is True
        assert cache.is_higher("BTCUSDT", 2) is True
        assert cache.is_higher("BTCUSDT", 3) is True

        # Duplicate trade with seq 2 should be rejected
        assert cache.is_higher("BTCUSDT", 2) is False

        # Out-of-order old trade with seq 1 should be rejected
        assert cache.is_higher("BTCUSDT", 1) is False

        # Newer trade with seq 4 should be accepted
        assert cache.is_higher("BTCUSDT", 4) is True

        # Cache should reflect highest sequence ID seen
        assert cache.get("BTCUSDT") == 4

    def test_cache_property_exposes_internal_dict(self):
        """Test cache property exposes internal dictionary."""
        cache = SimpleCache()
        cache.is_higher("BTCUSDT", 100)

        assert isinstance(cache.cache, dict)
        assert cache.cache["BTCUSDT"] == 100

from typing import Dict


class SimpleCache:
    """Simple cache for tracking sequence IDs to avoid duplicates.

    Used primarily for trade deduplication - tracks the highest sequence ID
    seen for each key and only accepts newer/higher values.

    Example usage:
        cache = SimpleCache()
        if cache.is_higher("BTCUSDT", 123):
            process_trade(trade_id=123)
    """

    def __init__(self):
        self._cache: Dict[str, int] = {}

    def is_higher(self, key: str, value: int) -> bool:
        """
        Check if value is higher than cached value for key.

        Returns True and updates cache if:
        - No entry exists for key, OR
        - New value is strictly higher than cached value

        Returns False if value <= cached value (duplicate or old data).

        Args:
            key: Identifier (e.g., symbol or symbol_seq combination)
            value: Value to compare (e.g., sequence ID)

        Returns:
            True if value should be processed, False if it's a duplicate
        """
        if key not in self._cache:
            self._cache[key] = value
            return True
        if value > self._cache[key]:
            self._cache[key] = value
            return True
        return False

    def is_different(self, key: str, value: int) -> bool:
        """Check if value is different from cached value for key."""
        if key not in self._cache:
            self._cache[key] = value
            return True
        return value != self._cache[key]

    def is_lower(self, key: str, value: int) -> bool:
        """Check if value is lower than cached value for key."""
        if key not in self._cache:
            self._cache[key] = value
            return True
        return value < self._cache[key]

    @property
    def cache(self) -> Dict[str, int]:
        """Expose internal cache for testing."""
        return self._cache

    def get(self, key: str) -> int | None:
        """Get cached value for key, or None if not exists."""
        return self._cache.get(key)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

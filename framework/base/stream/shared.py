"""
Shared state primitives for stream handlers.

Usage: create one StreamSharedContext per stream manager and pass it to handlers.
Components: manager-scoped value registry with lazy initialization helpers.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from msgspec import Struct, field

TValue = TypeVar("TValue")


class StreamSharedContext(Struct):
    """Manager-scoped registry for cross-handler runtime state.

    Attributes:
        values: Mutable key/value store shared by handlers in one manager instance.
    """

    values: dict[str, Any] = field(default_factory=dict)

    def get_or_create(self, key: str, factory: Callable[[], TValue]) -> TValue:
        """Return an existing shared value or create it lazily.

        Args:
            key: Stable registry key.
            factory: Zero-argument callable used to initialize missing values.

        Returns:
            TValue: Existing or newly created shared value.
        """
        value = self.values.get(key)
        if value is None:
            value = factory()
            self.values[key] = value
        return value  # type: ignore[return-value]

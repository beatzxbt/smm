"""Mapping utilities for enum translation and bidirectional lookup.

This module provides:
- `EnumMap` for enum<->string conversions
- `SimpleMap` for two-way key/value mappings
"""

from __future__ import annotations

from enum import Enum
from typing import Generic, TypeVar, cast

K = TypeVar("K")
V = TypeVar("V")
EnumK = TypeVar("EnumK", bound=Enum)


class EnumMap(Generic[EnumK]):
    """Bidirectional map between enum and string values.

    Args:
        enum_class: Enum class for type-checking and error reporting.
        mapping: Initial mapping from enum values to string values.
    """

    def __init__(self, enum_class: type[EnumK], mapping: dict[EnumK, str]) -> None:
        """Initialize enum<->string mapping tables.

        Args:
            enum_class: Enum class for type-checking and error reporting.
            mapping: Initial mapping from enum values to string values.
        """
        self._enum_to_str: dict[EnumK, str] = mapping.copy()
        self._str_to_enum: dict[str, EnumK] = {
            value: key for key, value in mapping.items()
        }
        self._enum_class = enum_class

    def enum_to_str(self, enum_val: EnumK) -> str:
        """Convert an enum value to its string representation.

        Args:
            enum_val: Enum value to convert.

        Returns:
            str: String representation for the enum value.
        """
        return self._enum_to_str[enum_val]

    def str_to_enum(self, str_val: str, default: EnumK | None = None) -> EnumK:
        """Convert a string value to its enum representation.

        Args:
            str_val: String value to convert.
            default: Optional fallback value when `str_val` is unknown.

        Returns:
            EnumK: Corresponding enum value or `default`.

        Raises:
            KeyError: If `str_val` is unknown and no default is provided.
        """
        if str_val in self._str_to_enum:
            return self._str_to_enum[str_val]
        if default is not None:
            return default
        raise KeyError(
            f"Unknown string value: {str_val} for enum {self._enum_class.__name__}"
        )


class SimpleMap(Generic[K, V]):
    """Simple K<->V bi-directional mapping implementation.

    Supports symmetric access:
    - `map[key] -> value`
    - `map[value] -> key`
    - `key in map` and `value in map`
    """

    def __init__(self, items: dict[K, V]) -> None:
        """Initialize map state from key/value pairs.

        Args:
            items: Initial mapping from keys to values.
        """
        self._k_to_v_map: dict[K, V] = items
        self._v_to_k_map: dict[V, K] = {value: key for key, value in items.items()}

    def get(self, key: K | V) -> V | K | None:
        """Return associated value/key for either side of the mapping.

        Args:
            key: Key or value to look up.

        Returns:
            V | K | None: Paired value/key, or None when missing.
        """
        if key in self._k_to_v_map:
            return self._k_to_v_map[cast(K, key)]
        if key in self._v_to_k_map:
            return self._v_to_k_map[cast(V, key)]
        return None

    def __getitem__(self, key: K | V) -> V | K:
        """Get the paired value/key using index access.

        Args:
            key: Key or value to look up.

        Returns:
            V | K: Paired value/key.

        Raises:
            KeyError: If neither side contains `key`.
        """
        if key in self._k_to_v_map:
            return self._k_to_v_map[cast(K, key)]
        if key in self._v_to_k_map:
            return self._v_to_k_map[cast(V, key)]
        raise KeyError(f"Key {key} not found in map")

    def __setitem__(self, key: K, value: V) -> None:
        """Set a key/value pair while keeping reverse mapping consistent.

        Args:
            key: Key to associate with `value`.
            value: Value to associate with `key`.
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
        """Return whether either side of the mapping contains `key`.

        Args:
            key: Key or value to test.

        Returns:
            bool: True when present, else False.
        """
        return key in self._k_to_v_map or key in self._v_to_k_map

    def __delitem__(self, key: K | V) -> None:
        """Delete a key or value and its corresponding pair.

        Args:
            key: Key or value to remove from the mapping.

        Raises:
            KeyError: If `key` does not exist on either side.
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
        """Return the number of stored key/value pairs.

        Returns:
            int: Mapping size.
        """
        return len(self._k_to_v_map)

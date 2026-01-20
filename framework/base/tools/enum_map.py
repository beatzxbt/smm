from typing import Dict, TypeVar, Generic
from enum import Enum


K = TypeVar("K", bound=Enum)


class EnumMap(Generic[K]):
    """Bidirectional map between enum and string values with explicit methods.

    Provides type-safe conversion between enum values and their string representations.

    Args:
        enum_class: The enum class for type checking
        mapping: Initial mapping from enum values to strings
    """

    def __init__(self, enum_class: type[K], mapping: Dict[K, str]):
        self._enum_to_str: Dict[K, str] = mapping.copy()
        self._str_to_enum: Dict[str, K] = {v: k for k, v in mapping.items()}
        self._enum_class = enum_class

    def enum_to_str(self, enum_val: K) -> str:
        """Convert enum value to its string representation."""
        return self._enum_to_str[enum_val]

    def str_to_enum(self, str_val: str, default: K | None = None) -> K:
        """Convert string to enum value, with optional default.

        Args:
            str_val: String value to convert
            default: Default enum value to return if string not found

        Returns:
            Corresponding enum value, or default if not found

        Raises:
            KeyError: If string not found and no default provided
        """
        if str_val in self._str_to_enum:
            return self._str_to_enum[str_val]
        if default is not None:
            return default
        raise KeyError(
            f"Unknown string value: {str_val} for enum {self._enum_class.__name__}"
        )

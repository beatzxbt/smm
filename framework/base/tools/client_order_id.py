"""Client order identifier generator utilities.

Usage: generate typed client order identifiers that satisfy venue length and
character constraints. Components: allowed-character enum and generator class.
"""

from __future__ import annotations

from enum import IntEnum

from mm_toolbox.time import time_monotonic_ns

from framework.base.common import ClientOrderId as ClientOrderIdValue


class AllowedOrderIdChars(IntEnum):
    """Allowed characters for a client order ID."""

    NUMERIC = 0
    ALPHABETIC = 1
    ALPHANUMERIC = 2


class ClientOrderId:
    """Generate an ID as <prefix><monotonic_ns><suffix>, left-truncating time if needed."""

    _last_time_ns: int = 0

    def __call__(
        self,
        length: int = 36,
        prefix: int | str = "",
        suffix: int | str = "",
        allowed_chars: AllowedOrderIdChars = AllowedOrderIdChars.ALPHANUMERIC,
    ) -> ClientOrderIdValue:
        """Generate a typed client order identifier.

        Args:
            length (int): Target total identifier length.
            prefix (int | str): Prefix inserted ahead of the timestamp segment.
            suffix (int | str): Suffix appended after the timestamp segment.
            allowed_chars (AllowedOrderIdChars): Character constraints for affixes.

        Returns:
            ClientOrderIdValue: Generated client order identifier.
        """
        return self.generate(length, prefix, suffix, allowed_chars)

    @classmethod
    def generate(
        cls,
        length: int = 36,
        prefix: int | str = "",
        suffix: int | str = "",
        allowed_chars: AllowedOrderIdChars = AllowedOrderIdChars.ALPHANUMERIC,
    ) -> ClientOrderIdValue:
        """Generate a typed client order identifier string.

        Args:
            length (int): Target total identifier length.
            prefix (int | str): Prefix inserted ahead of the timestamp segment.
            suffix (int | str): Suffix appended after the timestamp segment.
            allowed_chars (AllowedOrderIdChars): Character constraints for affixes.

        Returns:
            ClientOrderIdValue: Generated client order identifier.

        Raises:
            ValueError: If length or affix constraints are invalid.
        """
        if length <= 0:
            raise ValueError("Length must be >0")

        match allowed_chars:
            case AllowedOrderIdChars.NUMERIC:
                if isinstance(prefix, str) or isinstance(suffix, str):
                    raise ValueError(
                        "Prefix and suffix must be integers if allowed_chars is NUMERIC"
                    )
            case AllowedOrderIdChars.ALPHABETIC:
                if isinstance(prefix, int) or isinstance(suffix, int):
                    raise ValueError(
                        "Prefix and suffix must be strings if allowed_chars is ALPHABETIC"
                    )
            case AllowedOrderIdChars.ALPHANUMERIC:
                pass

        prefix_str = str(prefix)
        suffix_str = str(suffix)

        if len(prefix_str) + len(suffix_str) >= length:
            raise ValueError("Prefix + suffix length must be less than total length")

        available_time_len = length - len(prefix_str) - len(suffix_str)
        curr_time_ns = time_monotonic_ns()
        if curr_time_ns <= cls._last_time_ns:
            curr_time_ns = cls._last_time_ns + 1
        cls._last_time_ns = curr_time_ns
        time_str = str(curr_time_ns)
        time_part = (
            time_str[-available_time_len:]
            if len(time_str) > available_time_len
            else time_str
        )

        return ClientOrderIdValue(f"{prefix_str}{time_part}{suffix_str}")

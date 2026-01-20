from enum import IntEnum

from mm_toolbox.time import time_ns


class AllowedOrderIdChars(IntEnum):
    """Allowed characters for a client order ID."""

    NUMERIC = 0
    ALPHABETIC = 1
    ALPHANUMERIC = 2


class ClientOrderId:
    """Generate an ID as <prefix><time_ns><suffix>, left-truncating time if needed."""

    def __call__(
        self,
        length: int = 36,
        prefix: int | str = "",
        suffix: int | str = "",
        allowed_chars: AllowedOrderIdChars = AllowedOrderIdChars.ALPHANUMERIC,
    ) -> str:
        return self.generate(length, prefix, suffix, allowed_chars)

    @staticmethod
    def generate(
        length: int = 36,
        prefix: int | str = "",
        suffix: int | str = "",
        allowed_chars: AllowedOrderIdChars = AllowedOrderIdChars.ALPHANUMERIC,
    ) -> str:
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
        time_str = str(time_ns())
        time_part = (
            time_str[-available_time_len:]
            if len(time_str) > available_time_len
            else time_str
        )

        return f"{prefix_str}{time_part}{suffix_str}"

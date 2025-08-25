import time
import datetime
import ciso8601


def time_s() -> float:
    """
    Returns the current wall-clock time in seconds (float).
    """
    return time.time()


def time_ms() -> float:
    """
    Returns the current wall-clock time in milliseconds (float).
    """
    return time.time() * 1e3


def time_us() -> float:
    """
    Returns the current wall-clock time in microseconds (float).
    """
    return time.time() * 1e6


def time_ns() -> int:
    """
    Returns the current wall-clock time in nanoseconds (int).
    """
    return time.time_ns()


def iso8601_to_unix(timestamp) -> float:
    """
    Converts an ISO 8601 formatted timestamp to a Unix timestamp.

    Parameters:
        timestamp (str) : An ISO 8601 formatted date-time string.

    Returns:
        float: The Unix timestamp corresponding to the provided ISO 8601 date-time.
    """
    return ciso8601.parse_datetime(timestamp).timestamp()


def unix_to_iso8601(timestamp) -> str:
    """
    Converts a Unix timestamp to an ISO 8601 formatted timestamp with high precision.

    Parameters:
        timestamp (float): The Unix timestamp to convert. Can be in:
            - seconds (e.g., 1672574400.0)
            - milliseconds (e.g., 1672574400000.0)
            - microseconds (e.g., 1672574400000000.0)
            - nanoseconds (e.g., 1672574400000000000.0)

    Returns:
        str: The ISO 8601 formatted timestamp with full precision.
    """
    if timestamp >= 1e18:  # nanoseconds
        seconds = timestamp / 1e9
        fractional_part = int(timestamp % 1e9)
        fractional_str = f"{fractional_part:09d}"
    elif timestamp >= 1e15:  # microseconds
        seconds = timestamp / 1e6
        fractional_part = int(timestamp % 1e6)
        fractional_str = f"{fractional_part:06d}"
    elif timestamp >= 1e12:  # milliseconds
        seconds = timestamp / 1e3
        fractional_part = int(timestamp % 1e3)
        fractional_str = f"{fractional_part:03d}"
    else:  # seconds
        seconds = timestamp
        fractional_part = int((timestamp % 1) * 1e9)
        fractional_str = f"{fractional_part:09d}"[:3]

    # Get base time without fractional seconds
    base_time = datetime.datetime.fromtimestamp(int(seconds)).isoformat(
        timespec="seconds"
    )

    # Add high precision fractional seconds
    return f"{base_time}.{fractional_str}Z"


def time_iso8601() -> str:
    """
    Returns the current UTC time as 'YYYY-MM-DDTHH:MM:SS.fffZ'.

    Returns:
        str: The formatted date/time.
    """
    dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

import time
import datetime
import ciso8601


def time_s() -> int:
    """Returns the current wall-clock time in seconds."""
    return int(time.time())


def time_ms() -> int:
    """Returns the current wall-clock time in milliseconds."""
    return int(time.time() * 1e3)


def time_us() -> int:
    """Returns the current wall-clock time in microseconds."""
    return int(time.time() * 1e6)


def time_ns() -> int:
    """Returns the current wall-clock time in nanoseconds."""
    return time.time_ns()


def iso8601_to_unix(timestamp: str) -> int:
    """Converts an ISO 8601 formatted timestamp to a Unix timestamp (seconds)."""
    dt = ciso8601.parse_datetime(timestamp)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return int(dt.timestamp())


def unix_to_iso8601(timestamp: float) -> str:
    """Converts a Unix timestamp to an ISO 8601 formatted timestamp (UTC) with ms precision."""
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
        seconds = float(timestamp)
        fractional_part = int((seconds % 1) * 1e9)
        fractional_str = f"{fractional_part:09d}"[:3]

    # Get base time without fractional seconds
    base_time = datetime.datetime.fromtimestamp(
        int(seconds), tz=datetime.timezone.utc
    ).isoformat(timespec="seconds")

    # Add high precision fractional seconds
    return f"{base_time}.{fractional_str}Z"


def time_iso8601() -> str:
    """Returns the current UTC time as 'YYYY-MM-DDTHH:MM:SS.fffZ'."""
    dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

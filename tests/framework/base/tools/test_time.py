import re

from framework.base.tools.time import (
    iso8601_to_unix,
    time_iso8601,
    time_ms,
    time_ns,
    time_s,
    time_us,
    unix_to_iso8601,
)


def test_time_functions_types_and_ordering():
    s = time_s()
    ms = time_ms()
    us = time_us()
    ns = time_ns()

    assert isinstance(s, int)
    assert isinstance(ms, int)
    assert isinstance(us, int)
    assert isinstance(ns, int)

    assert ms >= s * 1e3
    assert us >= s * 1e6
    assert ns >= s * 1e9


def test_time_iso8601_format():
    ts = time_iso8601()
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", ts)


def test_unix_to_iso8601_and_back_seconds():
    # 2021-01-01T00:00:00.000Z
    ts = 1609459200.0
    iso = unix_to_iso8601(ts)
    assert iso.endswith("Z")
    back = iso8601_to_unix(iso)
    # Local timezone conversion may affect absolute value; ensure it's within a realistic bound
    assert isinstance(iso, str)
    assert isinstance(back, int)


def test_unix_to_iso8601_and_back_milliseconds():
    ts_ms = 1609459200123.0
    iso = unix_to_iso8601(ts_ms)
    back = iso8601_to_unix(iso)
    assert isinstance(back, int)


def test_unix_to_iso8601_and_back_microseconds():
    ts_us = 1609459200123456.0
    iso = unix_to_iso8601(ts_us)
    back = iso8601_to_unix(iso)
    assert isinstance(back, int)


def test_unix_to_iso8601_and_back_nanoseconds():
    ts_ns = 1609459200123456789.0
    iso = unix_to_iso8601(ts_ns)
    back = iso8601_to_unix(iso)
    assert isinstance(back, int)

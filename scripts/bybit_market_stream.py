"""Bybit market data stream runner for 300 alphabetically selected instruments.

Usage:
- Run `uv run python scripts/bybit_market_stream.py`.
- Press Ctrl+C to stop.

Components:
- BybitExchange + BybitMarketStreamManager initialization.
- Full market data subscriptions for 300 instruments from the exchange collection.
- Consumer loop logging stream messages to stdout at INFO level.
"""

# ruff: noqa: E402

from __future__ import annotations

import asyncio
import os
import signal
import sys
import time
from dataclasses import dataclass
from typing import Sequence

import uvloop

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

SYMBOL_LIMIT = 300

from framework.base.common import Instrument, Symbol
from framework.base.stream.models import ALL_MARKET_DATA_STREAM_TYPES, Msg
from framework.bybit.stream.manager import BybitMarketStreamManager
from framework.bybit.trading.exchange import BybitExchange
from mm_toolbox.logging.standard import FileLogHandler, Logger
from mm_toolbox.logging.standard.config import LoggerConfig
from mm_toolbox.time import time_ns


def build_logger() -> Logger:
    """Create a console logger for stream output.

    Returns:
        Logger: Logger configured to emit INFO logs to stdout.
    """
    log_path = "logs/bybit_market_stream.txt"
    log_dir = os.path.dirname(log_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    with open(log_path, "w", encoding="utf-8"):
        pass
    return Logger(
        name="bybit-linear",
        config=LoggerConfig(do_stdout=True),
        handlers=[
            FileLogHandler(
                filepath=log_path,
                create=True,
            )
        ],
    )


@dataclass(frozen=True)
class MessageRateSummary:
    """Summary statistics for message throughput.

    Attributes:
        min_rate (int): Minimum messages per second observed.
        max_rate (int): Maximum messages per second observed.
        mean_rate (float): Mean messages per second observed.
        total_messages (int): Total messages observed.
        window_seconds (int): Total seconds covered by the summary.
    """

    min_rate: int
    max_rate: int
    mean_rate: float
    total_messages: int
    window_seconds: int


@dataclass(frozen=True)
class MessageLatencySummary:
    """Summary statistics for message latency.

    Attributes:
        min_latency_ns (int): Minimum latency in nanoseconds observed.
        max_latency_ns (int): Maximum latency in nanoseconds observed.
        mean_latency_ns (float): Mean latency in nanoseconds observed.
        p50_latency_ns (int): 50th percentile latency in nanoseconds.
        p95_latency_ns (int): 95th percentile latency in nanoseconds.
        p99_latency_ns (int): 99th percentile latency in nanoseconds.
        total_messages (int): Total messages observed.
    """

    min_latency_ns: int
    max_latency_ns: int
    mean_latency_ns: float
    p50_latency_ns: int
    p95_latency_ns: int
    p99_latency_ns: int
    total_messages: int


@dataclass(frozen=True)
class MessageBackpressureSummary:
    """Summary statistics for message backpressure.

    Attributes:
        min_backpressure_ns (int): Minimum backpressure in nanoseconds observed.
        max_backpressure_ns (int): Maximum backpressure in nanoseconds observed.
        mean_backpressure_ns (float): Mean backpressure in nanoseconds observed.
        p50_backpressure_ns (int): 50th percentile backpressure in nanoseconds.
        p95_backpressure_ns (int): 95th percentile backpressure in nanoseconds.
        p99_backpressure_ns (int): 99th percentile backpressure in nanoseconds.
        total_messages (int): Total messages observed.
    """

    min_backpressure_ns: int
    max_backpressure_ns: int
    mean_backpressure_ns: float
    p50_backpressure_ns: int
    p95_backpressure_ns: int
    p99_backpressure_ns: int
    total_messages: int


@dataclass(frozen=True)
class MessageTypeSummary:
    """Summary statistics for a message type.

    Attributes:
        message_type (str): Message type name.
        total_messages (int): Total messages observed.
        rate_per_sec (float): Average messages per second over the window.
        min_latency_ns (int | None): Minimum latency in nanoseconds.
        max_latency_ns (int | None): Maximum latency in nanoseconds.
        mean_latency_ns (float | None): Mean latency in nanoseconds.
        p50_latency_ns (int | None): 50th percentile latency in nanoseconds.
        p95_latency_ns (int | None): 95th percentile latency in nanoseconds.
        p99_latency_ns (int | None): 99th percentile latency in nanoseconds.
        min_backpressure_ns (int | None): Minimum backpressure in nanoseconds.
        max_backpressure_ns (int | None): Maximum backpressure in nanoseconds.
        mean_backpressure_ns (float | None): Mean backpressure in nanoseconds.
        p50_backpressure_ns (int | None): 50th percentile backpressure in nanoseconds.
        p95_backpressure_ns (int | None): 95th percentile backpressure in nanoseconds.
        p99_backpressure_ns (int | None): 99th percentile backpressure in nanoseconds.
    """

    message_type: str
    total_messages: int
    rate_per_sec: float
    min_latency_ns: int | None
    max_latency_ns: int | None
    mean_latency_ns: float | None
    p50_latency_ns: int | None
    p95_latency_ns: int | None
    p99_latency_ns: int | None
    min_backpressure_ns: int | None
    max_backpressure_ns: int | None
    mean_backpressure_ns: float | None
    p50_backpressure_ns: int | None
    p95_backpressure_ns: int | None
    p99_backpressure_ns: int | None


def _percentile_from_sorted(samples: Sequence[int], percentile: float) -> int:
    """Calculate the percentile latency with linear interpolation.

    Args:
        samples (Sequence[int]): Sorted latency samples in nanoseconds.
        percentile (float): Percentile as a float in the range [0.0, 1.0].

    Returns:
        int: Percentile latency in nanoseconds.

    Raises:
        ValueError: If samples is empty.
    """
    if not samples:
        raise ValueError("No latency samples available for percentile computation.")
    if percentile <= 0.0:
        return samples[0]
    if percentile >= 1.0:
        return samples[-1]
    position = percentile * (len(samples) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(samples) - 1)
    if lower_index == upper_index:
        return samples[lower_index]
    lower_value = samples[lower_index]
    upper_value = samples[upper_index]
    weight = position - lower_index
    return int(lower_value + (upper_value - lower_value) * weight)


def _summarize_samples(
    samples: Sequence[int],
) -> tuple[int, int, float, int, int, int]:
    """Summarize sample statistics including percentiles.

    Args:
        samples (Sequence[int]): Raw samples in nanoseconds.

    Returns:
        tuple[int, int, float, int, int, int]: Min, max, mean, p50, p95, p99.

    Raises:
        ValueError: If samples is empty.
    """
    if not samples:
        raise ValueError("No samples available for summary computation.")
    sorted_samples = sorted(samples)
    min_value = sorted_samples[0]
    max_value = sorted_samples[-1]
    mean_value = sum(sorted_samples) / len(sorted_samples)
    p50_value = _percentile_from_sorted(sorted_samples, 0.50)
    p95_value = _percentile_from_sorted(sorted_samples, 0.95)
    p99_value = _percentile_from_sorted(sorted_samples, 0.99)
    return min_value, max_value, mean_value, p50_value, p95_value, p99_value


def _format_ms(value_ns: float | int | None) -> str:
    """Format a nanosecond value as milliseconds for table output.

    Args:
        value_ns (float | int | None): Latency value in nanoseconds.

    Returns:
        str: Formatted milliseconds string.
    """
    if value_ns is None:
        return "-"
    return f"{value_ns / 1_000_000:.3f}"


def _format_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    """Build an ASCII table with aligned columns.

    Args:
        headers (Sequence[str]): Column headers.
        rows (Sequence[Sequence[str]]): Table rows.

    Returns:
        list[str]: Lines of the formatted table.
    """
    if not rows:
        return []
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    header_line = " | ".join(
        header.ljust(widths[index]) for index, header in enumerate(headers)
    )
    divider_line = "-+-".join("-" * width for width in widths)
    lines = [header_line, divider_line]
    for row in rows:
        lines.append(
            " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))
        )
    return lines


class MessageRateTracker:
    """Track per-second message throughput during a run.

    Counts messages per integer second based on monotonic time and summarizes
    min/max/mean message rates across the observed window.
    """

    def __init__(self) -> None:
        """Initialize the tracker state."""
        self._counts: dict[int, int] = {}
        self._start_sec: int | None = None
        self._end_sec: int | None = None

    def record(self, now: float | None = None) -> None:
        """Record a message arrival time.

        Args:
            now (float | None): Optional monotonic timestamp in seconds.
        """
        timestamp = now if now is not None else time.monotonic()
        second = int(timestamp)
        if self._start_sec is None or second < self._start_sec:
            self._start_sec = second
        if self._end_sec is None or second > self._end_sec:
            self._end_sec = second
        self._counts[second] = self._counts.get(second, 0) + 1

    def summarize(self) -> MessageRateSummary | None:
        """Summarize message throughput statistics.

        Returns:
            MessageRateSummary | None: Summary stats or None if no messages seen.
        """
        if self._start_sec is None or self._end_sec is None:
            return None
        window_seconds = self._end_sec - self._start_sec + 1
        rates = [
            self._counts.get(second, 0)
            for second in range(self._start_sec, self._end_sec + 1)
        ]
        total_messages = sum(rates)
        return MessageRateSummary(
            min_rate=min(rates),
            max_rate=max(rates),
            mean_rate=total_messages / window_seconds,
            total_messages=total_messages,
            window_seconds=window_seconds,
        )


class MessageLatencyTracker:
    """Track message latency during a run.

    Attributes:
        _count (int): Number of message latencies recorded.
        _sum_latency_ns (int): Sum of latencies in nanoseconds.
        _min_latency_ns (int | None): Minimum latency observed.
        _max_latency_ns (int | None): Maximum latency observed.
        _latencies_ns (list[int]): Raw latency samples in nanoseconds.
    """

    def __init__(self) -> None:
        """Initialize the tracker state."""
        self._count = 0
        self._sum_latency_ns = 0
        self._min_latency_ns: int | None = None
        self._max_latency_ns: int | None = None
        self._latencies_ns: list[int] = []

    def record(self, latency_ns: int) -> None:
        """Record a message latency.

        Args:
            latency_ns (int): Latency in nanoseconds.
        """
        self._count += 1
        self._sum_latency_ns += latency_ns
        self._latencies_ns.append(latency_ns)
        if self._min_latency_ns is None or latency_ns < self._min_latency_ns:
            self._min_latency_ns = latency_ns
        if self._max_latency_ns is None or latency_ns > self._max_latency_ns:
            self._max_latency_ns = latency_ns

    def summarize(self) -> MessageLatencySummary | None:
        """Summarize message latency statistics.

        Returns:
            MessageLatencySummary | None: Summary stats or None if no messages seen.
        """
        if (
            self._count == 0
            or self._min_latency_ns is None
            or self._max_latency_ns is None
        ):
            return None
        (
            min_latency,
            max_latency,
            mean_latency,
            p50_latency,
            p95_latency,
            p99_latency,
        ) = _summarize_samples(self._latencies_ns)
        return MessageLatencySummary(
            min_latency_ns=min_latency,
            max_latency_ns=max_latency,
            mean_latency_ns=mean_latency,
            p50_latency_ns=p50_latency,
            p95_latency_ns=p95_latency,
            p99_latency_ns=p99_latency,
            total_messages=self._count,
        )


class MessageBackpressureTracker:
    """Track message backpressure during a run.

    Attributes:
        _count (int): Number of message backpressure samples recorded.
        _sum_backpressure_ns (int): Sum of backpressure values in nanoseconds.
        _min_backpressure_ns (int | None): Minimum backpressure observed.
        _max_backpressure_ns (int | None): Maximum backpressure observed.
        _backpressures_ns (list[int]): Raw backpressure samples in nanoseconds.
    """

    def __init__(self) -> None:
        """Initialize the tracker state."""
        self._count = 0
        self._sum_backpressure_ns = 0
        self._min_backpressure_ns: int | None = None
        self._max_backpressure_ns: int | None = None
        self._backpressures_ns: list[int] = []

    def record(self, backpressure_ns: int) -> None:
        """Record a message backpressure value.

        Args:
            backpressure_ns (int): Backpressure in nanoseconds.
        """
        self._count += 1
        self._sum_backpressure_ns += backpressure_ns
        self._backpressures_ns.append(backpressure_ns)
        if (
            self._min_backpressure_ns is None
            or backpressure_ns < self._min_backpressure_ns
        ):
            self._min_backpressure_ns = backpressure_ns
        if (
            self._max_backpressure_ns is None
            or backpressure_ns > self._max_backpressure_ns
        ):
            self._max_backpressure_ns = backpressure_ns

    def summarize(self) -> MessageBackpressureSummary | None:
        """Summarize backpressure statistics.

        Returns:
            MessageBackpressureSummary | None: Summary stats or None if no messages seen.
        """
        if (
            self._count == 0
            or self._min_backpressure_ns is None
            or self._max_backpressure_ns is None
        ):
            return None
        (
            min_backpressure,
            max_backpressure,
            mean_backpressure,
            p50_backpressure,
            p95_backpressure,
            p99_backpressure,
        ) = _summarize_samples(self._backpressures_ns)
        return MessageBackpressureSummary(
            min_backpressure_ns=min_backpressure,
            max_backpressure_ns=max_backpressure,
            mean_backpressure_ns=mean_backpressure,
            p50_backpressure_ns=p50_backpressure,
            p95_backpressure_ns=p95_backpressure,
            p99_backpressure_ns=p99_backpressure,
            total_messages=self._count,
        )


class MessageTypeTracker:
    """Track counts and latency samples by message type."""

    def __init__(self) -> None:
        """Initialize the tracker state."""
        self._counts: dict[str, int] = {}
        self._latencies_ns: dict[str, list[int]] = {}
        self._backpressures_ns: dict[str, list[int]] = {}

    def record(
        self, message_type: str, latency_ns: int | None, backpressure_ns: int | None
    ) -> None:
        """Record a message type occurrence and optional timing stats.

        Args:
            message_type (str): Message type name.
            latency_ns (int | None): Latency in nanoseconds, if available.
            backpressure_ns (int | None): Backpressure in nanoseconds, if available.
        """
        self._counts[message_type] = self._counts.get(message_type, 0) + 1
        if latency_ns is not None:
            if message_type not in self._latencies_ns:
                self._latencies_ns[message_type] = []
            self._latencies_ns[message_type].append(latency_ns)
        if backpressure_ns is not None:
            if message_type not in self._backpressures_ns:
                self._backpressures_ns[message_type] = []
            self._backpressures_ns[message_type].append(backpressure_ns)

    def summarize(self, window_seconds: int) -> list[MessageTypeSummary]:
        """Summarize message stats by type.

        Args:
            window_seconds (int): Total seconds covered by the summary window.

        Returns:
            list[MessageTypeSummary]: Summaries ordered by message count.
        """
        summaries: list[MessageTypeSummary] = []
        for message_type, count in self._counts.items():
            samples = self._latencies_ns.get(message_type, [])
            if samples:
                (
                    min_latency,
                    max_latency,
                    mean_latency,
                    p50_latency,
                    p95_latency,
                    p99_latency,
                ) = _summarize_samples(samples)
            else:
                min_latency = None
                max_latency = None
                mean_latency = None
                p50_latency = None
                p95_latency = None
                p99_latency = None
            backpressure_samples = self._backpressures_ns.get(message_type, [])
            if backpressure_samples:
                (
                    min_backpressure,
                    max_backpressure,
                    mean_backpressure,
                    p50_backpressure,
                    p95_backpressure,
                    p99_backpressure,
                ) = _summarize_samples(backpressure_samples)
            else:
                min_backpressure = None
                max_backpressure = None
                mean_backpressure = None
                p50_backpressure = None
                p95_backpressure = None
                p99_backpressure = None
            summaries.append(
                MessageTypeSummary(
                    message_type=message_type,
                    total_messages=count,
                    rate_per_sec=count / window_seconds,
                    min_latency_ns=min_latency,
                    max_latency_ns=max_latency,
                    mean_latency_ns=mean_latency,
                    p50_latency_ns=p50_latency,
                    p95_latency_ns=p95_latency,
                    p99_latency_ns=p99_latency,
                    min_backpressure_ns=min_backpressure,
                    max_backpressure_ns=max_backpressure,
                    mean_backpressure_ns=mean_backpressure,
                    p50_backpressure_ns=p50_backpressure,
                    p95_backpressure_ns=p95_backpressure,
                    p99_backpressure_ns=p99_backpressure,
                )
            )
        return sorted(
            summaries, key=lambda summary: summary.total_messages, reverse=True
        )


async def resolve_instruments(
    exchange: BybitExchange, symbols: Sequence[Symbol]
) -> list[Instrument]:
    """Resolve Bybit instruments for the given symbols.

    Args:
        exchange (BybitExchange): Exchange client used for symbol resolution.
        symbols (Sequence[str]): Symbol strings to resolve (e.g. "BTCUSDT").

    Returns:
        list[Instrument]: Resolved instrument objects.
    """
    instruments: list[Instrument] = []
    for symbol in symbols:
        instruments.append(await exchange.resolve_instrument(symbol))
    return instruments


async def consume_messages(
    queue: asyncio.Queue[Msg],
    logger: Logger,
    rate_tracker: MessageRateTracker,
    latency_tracker: MessageLatencyTracker,
    backpressure_tracker: MessageBackpressureTracker,
    type_tracker: MessageTypeTracker,
) -> None:
    """Consume stream messages and log them at INFO level.

    Args:
        queue (asyncio.Queue[Msg]): Queue receiving stream messages.
        logger (Logger): Logger for INFO output.
        rate_tracker (MessageRateTracker): Tracker for message throughput.
        latency_tracker (MessageLatencyTracker): Tracker for message latency.
        backpressure_tracker (MessageBackpressureTracker): Tracker for queue backpressure.
        type_tracker (MessageTypeTracker): Tracker for per-type stats.
    """
    while True:
        msg = await queue.get()
        rate_tracker.record()
        moments = getattr(msg, "moments", None)
        latency_ns: int | None = None
        backpressure_ns: int | None = None
        if moments is not None:
            latency_ns = moments.recv_time_ns - moments.exch_time_ns
            latency_tracker.record(latency_ns)
            backpressure_ns = time_ns() - moments.recv_time_ns
            backpressure_tracker.record(backpressure_ns)
        type_tracker.record(msg.__class__.__name__, latency_ns, backpressure_ns)
        logger.info(str(msg))


class StreamRunner:
    """Encapsulates stream runner state for clean shutdown handling."""

    def __init__(self) -> None:
        """Initialize runner state."""
        self.logger: Logger | None = None
        self.exchange: BybitExchange | None = None
        self.manager: BybitMarketStreamManager | None = None
        self.consumer_task: asyncio.Task[None] | None = None
        self.rate_tracker = MessageRateTracker()
        self.latency_tracker = MessageLatencyTracker()
        self.backpressure_tracker = MessageBackpressureTracker()
        self.type_tracker = MessageTypeTracker()

    def print_summary(self) -> None:
        """Print rate summary to stdout (sync, for use after loop shutdown)."""
        summary = self.rate_tracker.summarize()
        if summary is None:
            print("No messages received; rate stats unavailable.")
            print("Shutdown complete.")
            return
        latency_summary = self.latency_tracker.summarize()
        backpressure_summary = self.backpressure_tracker.summarize()
        message_type_summaries = self.type_tracker.summarize(summary.window_seconds)

        print("Message summary:")
        print("Timings in ms.")
        rate_headers = ["Window", "Total", "Min rate", "Max rate", "Mean rate"]
        rate_row = [
            str(summary.window_seconds),
            str(summary.total_messages),
            str(summary.min_rate),
            str(summary.max_rate),
            f"{summary.mean_rate:.2f}",
        ]
        print("Rates:")
        for line in _format_table(rate_headers, [rate_row]):
            print(line)

        latency_headers = ["Count", "Min", "P50", "P95", "P99", "Max", "Mean"]
        latency_row = [
            str(latency_summary.total_messages) if latency_summary else "0",
            _format_ms(
                None if latency_summary is None else latency_summary.min_latency_ns
            ),
            _format_ms(
                None if latency_summary is None else latency_summary.p50_latency_ns
            ),
            _format_ms(
                None if latency_summary is None else latency_summary.p95_latency_ns
            ),
            _format_ms(
                None if latency_summary is None else latency_summary.p99_latency_ns
            ),
            _format_ms(
                None if latency_summary is None else latency_summary.max_latency_ns
            ),
            _format_ms(
                None if latency_summary is None else latency_summary.mean_latency_ns
            ),
        ]
        print("")
        print("Latency:")
        for line in _format_table(latency_headers, [latency_row]):
            print(line)

        backpressure_headers = ["Count", "Min", "P50", "P95", "P99", "Max", "Mean"]
        backpressure_row = [
            str(backpressure_summary.total_messages) if backpressure_summary else "0",
            _format_ms(
                None
                if backpressure_summary is None
                else backpressure_summary.min_backpressure_ns
            ),
            _format_ms(
                None
                if backpressure_summary is None
                else backpressure_summary.p50_backpressure_ns
            ),
            _format_ms(
                None
                if backpressure_summary is None
                else backpressure_summary.p95_backpressure_ns
            ),
            _format_ms(
                None
                if backpressure_summary is None
                else backpressure_summary.p99_backpressure_ns
            ),
            _format_ms(
                None
                if backpressure_summary is None
                else backpressure_summary.max_backpressure_ns
            ),
            _format_ms(
                None
                if backpressure_summary is None
                else backpressure_summary.mean_backpressure_ns
            ),
        ]
        print("")
        print("Backpressure:")
        for line in _format_table(backpressure_headers, [backpressure_row]):
            print(line)

        if not message_type_summaries:
            print("No message type stats available.")
        else:
            print("")
            type_rate_headers = ["Type", "Count", "Rate/s"]
            type_rate_rows = [
                [
                    type_summary.message_type,
                    str(type_summary.total_messages),
                    f"{type_summary.rate_per_sec:.2f}",
                ]
                for type_summary in message_type_summaries
            ]
            print("Message type rates:")
            for line in _format_table(type_rate_headers, type_rate_rows):
                print(line)

            type_latency_headers = ["Type", "Min", "P50", "P95", "P99", "Max", "Mean"]
            type_latency_rows = [
                [
                    type_summary.message_type,
                    _format_ms(type_summary.min_latency_ns),
                    _format_ms(type_summary.p50_latency_ns),
                    _format_ms(type_summary.p95_latency_ns),
                    _format_ms(type_summary.p99_latency_ns),
                    _format_ms(type_summary.max_latency_ns),
                    _format_ms(type_summary.mean_latency_ns),
                ]
                for type_summary in message_type_summaries
            ]
            print("")
            print("Message type latency:")
            for line in _format_table(type_latency_headers, type_latency_rows):
                print(line)

            type_backpressure_headers = [
                "Type",
                "Min",
                "P50",
                "P95",
                "P99",
                "Max",
                "Mean",
            ]
            type_backpressure_rows = [
                [
                    type_summary.message_type,
                    _format_ms(type_summary.min_backpressure_ns),
                    _format_ms(type_summary.p50_backpressure_ns),
                    _format_ms(type_summary.p95_backpressure_ns),
                    _format_ms(type_summary.p99_backpressure_ns),
                    _format_ms(type_summary.max_backpressure_ns),
                    _format_ms(type_summary.mean_backpressure_ns),
                ]
                for type_summary in message_type_summaries
            ]
            print("")
            print("Message type backpressure:")
            for line in _format_table(
                type_backpressure_headers, type_backpressure_rows
            ):
                print(line)
        print("Shutdown complete.")


async def run(runner: StreamRunner) -> None:
    """Run the Bybit market data stream and log messages.

    Args:
        runner (StreamRunner): Runner instance holding shared state.
    """
    runner.logger = build_logger()
    runner.exchange = BybitExchange(
        logger=runner.logger,
        load_secrets=False,
    )
    consumer_queue: asyncio.Queue[Msg] = asyncio.Queue()
    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        """Signal handler that triggers graceful shutdown."""
        runner.logger.info("Received shutdown signal.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    try:
        runner.manager = await BybitMarketStreamManager.create(
            exchange=runner.exchange,
            logger=runner.logger,
            consumer_queues=[consumer_queue],
        )
        collection_instruments = runner.manager.instrument_collection.instruments
        instruments = sorted(
            collection_instruments,
            key=lambda instrument: instrument.symbol,
        )[:SYMBOL_LIMIT]
        await runner.manager.start()
        await runner.manager.subscribe(instruments, set(ALL_MARKET_DATA_STREAM_TYPES))
        runner.logger.info(
            f"Subscribed to {len(instruments)} instruments (full market data)."
        )

        runner.consumer_task = asyncio.create_task(
            consume_messages(
                consumer_queue,
                runner.logger,
                runner.rate_tracker,
                runner.latency_tracker,
                runner.backpressure_tracker,
                runner.type_tracker,
            )
        )
        await stop_event.wait()
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        if runner.logger:
            runner.logger.error(f"Stream runner failed: {exc}")
        raise
    finally:
        if runner.manager is not None:
            await runner.manager.stop()
        if runner.consumer_task is not None:
            runner.consumer_task.cancel()
            await asyncio.gather(runner.consumer_task, return_exceptions=True)
            runner.consumer_task = None
        if runner.exchange is not None:
            await runner.exchange.close_clients()


def main() -> None:
    """Entry point with graceful shutdown and summary output."""
    runner = StreamRunner()
    try:
        uvloop.run(run(runner))
    except KeyboardInterrupt:
        pass
    finally:
        runner.print_summary()
        sys.stdout.flush()
        uvloop.run(asyncio.sleep(10))


if __name__ == "__main__":
    main()

"""Shared schema primitives for stream and trading models.

Provides:
- Message identity and causal correlation metadata
- Timing metadata for latency measurements
- Envelope base structs shared across normalized message domains
"""

from __future__ import annotations

from itertools import count
from os import getpid

from msgspec import Struct, field

from framework.base.common import Instrument, Venue
from mm_toolbox.time import time_ns


_PROCESS_PID = getpid()
_MESSAGE_ID_SEQUENCE = count()


class MessageId(Struct, frozen=True):
    """Process-local identifier for a normalized message.

    The identifier combines a process-stable PID, the receive timestamp that
    anchored the message, and a per-process sequence number to guarantee
    uniqueness even when multiple messages share the same receive timestamp.

    Attributes:
        recv_time_ns: Local receive timestamp associated with the message.
        seq: Monotonic per-process sequence number for tie-breaking.
        pid: Process identifier for the process that created the message.
    """

    recv_time_ns: int = field(default_factory=time_ns)
    seq: int = field(default_factory=_MESSAGE_ID_SEQUENCE.__next__)
    pid: int = _PROCESS_PID

    def full_id(self) -> str:
        """Return the identifier encoded as a stable string.

        Returns:
            str: Colon-delimited identifier string.
        """
        return f"{self.pid}:{self.recv_time_ns}:{self.seq}"


class Moments(Struct, frozen=True):
    """Timing information for a message.

    Attributes:
        exch_time_ns: Timestamp in nanoseconds reported by the upstream source.
        recv_time_ns: Local receive timestamp in nanoseconds.
    """

    exch_time_ns: int = field(default_factory=time_ns)
    recv_time_ns: int = field(default_factory=time_ns)

    def elapsed_since_exch_ns(self) -> int:
        """Return elapsed nanoseconds since the exchange emitted the message.

        Returns:
            int: Non-negative elapsed nanoseconds.
        """
        return time_ns() - self.exch_time_ns

    def elapsed_since_recv_ns(self) -> int:
        """Return elapsed nanoseconds since the client received the message.

        Returns:
            int: Non-negative elapsed nanoseconds.
        """
        return time_ns() - self.recv_time_ns

    def latency_ms(self) -> float:
        """Return exchange-to-receive latency in milliseconds.

        Returns:
            float: Non-negative latency from exchange timestamp to local receive timestamp.
        """
        return max((self.recv_time_ns - self.exch_time_ns) / 1_000_000.0, 0.0)


class CorrelatedSchema(Struct, frozen=True):
    """Base schema for objects that need local and causal identifiers.

    Attributes:
        id: Unique identifier for this specific message instance.
        origin_id: Identifier of the upstream event that caused this message.
    """

    id: MessageId
    origin_id: MessageId


class EnvelopeSchema(CorrelatedSchema, frozen=True):
    """Base schema for normalized messages carrying timing and instrument scope.

    Attributes:
        moments: Exchange and local receive timestamps for the message.
        instrument: Instrument the message data applies to.
    """

    moments: Moments
    instrument: Instrument

    @property
    def venue(self) -> Venue:
        """Return the venue inferred from the instrument.

        Returns:
            Venue: Venue associated with the instrument.
        """
        return self.instrument.venue

"""Tests for framework.base.schema module.

Tests cover:
- MessageId identity and uniqueness behavior
- Moments timing helpers and latency calculations
- CorrelatedSchema and EnvelopeSchema primitive envelope behavior

Tests are organized by dependency layer:
1. Primitives: MessageId, Moments
2. Composites: CorrelatedSchema, EnvelopeSchema
"""

from __future__ import annotations

import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from multiprocessing.connection import Connection

import pytest

from framework.base.common import Asset, Instrument, InstrumentType, Symbol, Venue
from framework.base.schema import CorrelatedSchema, EnvelopeSchema, MessageId, Moments


def _emit_child_message_id(recv_time_ns: int, child_conn: Connection) -> None:
    """Create a MessageId in a child process and send identity fields.

    Args:
        recv_time_ns: Receive timestamp to use for the generated identifier.
        child_conn: One-way pipe connection back to the parent process.
    """
    msg_id = MessageId(recv_time_ns=recv_time_ns)
    child_conn.send((msg_id.pid, msg_id.full_id()))
    child_conn.close()


@pytest.fixture
def sample_instrument() -> Instrument:
    """Return a reusable instrument for schema envelope tests.

    Returns:
        Instrument: Canonical instrument used across schema tests.
    """
    return Instrument(
        venue=Venue.BINANCE_USDM,
        base=Asset("BTC"),
        quote=Asset("USDT"),
        symbol=Symbol("BTCUSDT"),
        code=1,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )


class TestMoments:
    """Test Moments timing struct."""

    def test_creation_with_defaults(self):
        """Test creating Moments with default time values."""
        moments = Moments()
        assert moments.exch_time_ns > 0
        assert moments.recv_time_ns > 0

    def test_creation_with_explicit_times(self):
        """Test creating Moments with explicit time values."""
        moments = Moments(exch_time_ns=1000, recv_time_ns=2000)
        assert moments.exch_time_ns == 1000
        assert moments.recv_time_ns == 2000

    def test_elapsed_since_exch_ns_is_nonnegative(self):
        """Test elapsed time since exchange is non-negative."""
        moments = Moments()
        assert moments.elapsed_since_exch_ns() >= 0

    def test_elapsed_since_recv_ns_is_nonnegative(self):
        """Test elapsed time since receive is non-negative."""
        moments = Moments()
        assert moments.elapsed_since_recv_ns() >= 0

    def test_elapsed_methods_increase_over_time(self):
        """Test that elapsed-from-exchange returns a positive value."""
        moments = Moments(exch_time_ns=100, recv_time_ns=100)
        assert moments.elapsed_since_exch_ns() > 0

    def test_latency_ms_returns_positive_delta(self):
        """Test latency_ms returns exchange-to-receive latency in milliseconds."""
        moments = Moments(exch_time_ns=1_000_000, recv_time_ns=3_500_000)
        assert moments.latency_ms() == 2.5

    def test_latency_ms_clamps_negative_delta_to_zero(self):
        """Test latency_ms never returns negative values."""
        moments = Moments(exch_time_ns=3000, recv_time_ns=1000)
        assert moments.latency_ms() == 0.0


class TestMessageId:
    """Test MessageId identity struct."""

    def test_defaults_use_process_pid_recv_time_and_sequence(self):
        """Test MessageId populates pid, recv time, and sequence automatically."""
        msg_id = MessageId()

        assert msg_id.pid > 0
        assert msg_id.recv_time_ns > 0
        assert msg_id.seq >= 0

    def test_explicit_recv_time_override(self):
        """Test MessageId supports explicit receive timestamp override."""
        msg_id = MessageId(recv_time_ns=1234)
        assert msg_id.recv_time_ns == 1234

    def test_full_id_includes_all_components(self):
        """Test full_id renders a stable string encoding."""
        msg_id = MessageId(pid=11, recv_time_ns=22, seq=33)
        assert msg_id.full_id() == "11:22:33"

    def test_full_id_components_match_fields(self):
        """Test full_id components round-trip to struct fields."""
        msg_id = MessageId()
        pid_str, recv_time_ns_str, seq_str = msg_id.full_id().split(":")

        assert int(pid_str) == msg_id.pid
        assert int(recv_time_ns_str) == msg_id.recv_time_ns
        assert int(seq_str) == msg_id.seq

    def test_uniqueness_same_recv_time(self):
        """Test ids remain unique when all share the same recv timestamp."""
        recv_time_ns = 1_234_567_890
        msg_ids = [MessageId(recv_time_ns=recv_time_ns) for _ in range(512)]

        assert len({msg_id.seq for msg_id in msg_ids}) == len(msg_ids)
        assert len({msg_id.full_id() for msg_id in msg_ids}) == len(msg_ids)
        assert {msg_id.recv_time_ns for msg_id in msg_ids} == {recv_time_ns}

    def test_uniqueness_under_threaded_creation(self):
        """Test concurrent id creation still produces unique full ids."""
        recv_time_ns = 9_876_543_210
        num_ids = 1024

        def create_full_id(_: int) -> str:
            """Create a full id with a shared receive timestamp.

            Args:
                _: Map index from executor.

            Returns:
                str: Full identifier string.
            """
            return MessageId(recv_time_ns=recv_time_ns).full_id()

        with ThreadPoolExecutor(max_workers=8) as executor:
            full_ids = list(executor.map(create_full_id, range(num_ids)))

        assert len(full_ids) == num_ids
        assert len(set(full_ids)) == num_ids

    def test_uniqueness_across_processes(self):
        """Test process PID component keeps ids unique across processes."""
        recv_time_ns = 5_555_555_555
        parent_msg_id = MessageId(recv_time_ns=recv_time_ns)

        ctx = multiprocessing.get_context("spawn")
        parent_conn, child_conn = ctx.Pipe(duplex=False)
        process = ctx.Process(
            target=_emit_child_message_id,
            args=(recv_time_ns, child_conn),
        )

        try:
            process.start()
            child_conn.close()

            assert parent_conn.poll(5.0)
            child_pid, child_full_id = parent_conn.recv()

            process.join(timeout=5.0)
            assert process.exitcode == 0
        finally:
            parent_conn.close()
            if process.is_alive():
                process.terminate()
                process.join(timeout=5.0)

        assert child_pid != parent_msg_id.pid
        assert child_full_id != parent_msg_id.full_id()


class TestCorrelatedSchema:
    """Test CorrelatedSchema envelope correlation primitives."""

    def test_creation_with_distinct_ids(self):
        """Test CorrelatedSchema stores independent local and origin identifiers."""
        recv_time_ns = 1_000_000
        current_id = MessageId(recv_time_ns=recv_time_ns)
        origin_id = MessageId(recv_time_ns=recv_time_ns)

        schema = CorrelatedSchema(id=current_id, origin_id=origin_id)

        assert schema.id == current_id
        assert schema.origin_id == origin_id
        assert schema.id != schema.origin_id


class TestEnvelopeSchema:
    """Test EnvelopeSchema normalized envelope primitives."""

    def test_creation_with_valid_data(self, sample_instrument: Instrument):
        """Test EnvelopeSchema stores full envelope and venue information."""
        moments = Moments(exch_time_ns=1000, recv_time_ns=2000)
        message_id = MessageId(recv_time_ns=moments.recv_time_ns)

        schema = EnvelopeSchema(
            id=message_id,
            origin_id=message_id,
            moments=moments,
            instrument=sample_instrument,
        )

        assert schema.id == message_id
        assert schema.origin_id == message_id
        assert schema.moments == moments
        assert schema.instrument == sample_instrument
        assert schema.venue == Venue.BINANCE_USDM

    def test_venue_property_reflects_instrument_venue(self):
        """Test EnvelopeSchema.venue delegates to the instrument venue field."""
        instrument = Instrument(
            venue=Venue.BYBIT,
            base=Asset("ETH"),
            quote=Asset("USDT"),
            symbol=Symbol("ETHUSDT"),
            code=2,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        moments = Moments(exch_time_ns=10, recv_time_ns=20)
        message_id = MessageId(recv_time_ns=moments.recv_time_ns)

        schema = EnvelopeSchema(
            id=message_id,
            origin_id=message_id,
            moments=moments,
            instrument=instrument,
        )

        assert schema.venue == Venue.BYBIT

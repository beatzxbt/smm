"""Tests for framework.base.trading.time_sync.TimeSync.

Coverage includes:
- Initialization defaults and custom parameters
- time_ms, offset_ms, is_stale properties
- sync() offset computation and EMA update
- start()/stop() lifecycle and periodic loop
- Error handling
"""

from __future__ import annotations

import asyncio
from typing import override
from unittest.mock import AsyncMock

import aiohttp
import pytest

from framework.base.common import Venue
from framework.base.trading.time_sync import TimeSync
from mm_toolbox.logging.standard import Logger


@pytest.fixture
def fake_session() -> AsyncMock:
    """Mock aiohttp.ClientSession that does nothing."""
    return AsyncMock(spec=aiohttp.ClientSession)


class FakeTimeSync(TimeSync):
    """TimeSync stub with configurable server time for testing."""

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        server_time_ms: int = 0,
        **kwargs: float,
    ) -> None:
        super().__init__(venue=venue, logger=logger, **kwargs)
        self.server_time_ms = server_time_ms
        self.fetch_call_count = 0

    @override
    async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
        self.fetch_call_count += 1
        return self.server_time_ms


class TestTimeSyncInit:
    """Test TimeSync initialization and default values."""

    def test_default_init_parameters(self, test_logger: Logger) -> None:
        """Verify that a freshly initialized TimeSync has sensible defaults."""
        ts = FakeTimeSync(venue=Venue.BYBIT, logger=test_logger)

        assert ts.venue == Venue.BYBIT
        assert ts.offset_ms == 0
        assert ts.time_ms >= 0
        assert ts.is_stale is True

    def test_custom_parameters(self, test_logger: Logger) -> None:
        """Verify that custom constructor parameters are stored."""
        ts = FakeTimeSync(
            venue=Venue.OKX,
            logger=test_logger,
            half_life_s=60.0,
            sync_interval_s=30.0,
            stale_threshold_s=90.0,
        )

        assert ts.venue == Venue.OKX
        assert ts.offset_ms == 0

    def test_is_stale_before_first_sync(self, test_logger: Logger) -> None:
        """is_stale must return True before any sync has occurred."""
        ts = FakeTimeSync(venue=Venue.BYBIT, logger=test_logger)
        assert ts.is_stale is True


class TestTimeSyncSync:
    """Test the sync() method — offset computation and EMA update."""

    @pytest.mark.asyncio
    async def test_sync_bootstrap_first_sample(
        self,
        test_logger: Logger,
        fake_session: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """First sync bootstraps the offset directly (no EMA smoothing yet)."""
        ts = FakeTimeSync(
            venue=Venue.BYBIT,
            logger=test_logger,
            server_time_ms=5000,
        )
        monkeypatch.setattr(
            "framework.base.trading.time_sync.time_ns",
            lambda: 1_000_000_000,
        )

        await ts.start(fake_session)

        assert ts.offset_ms == 4000

    @pytest.mark.asyncio
    async def test_sync_updates_ema(
        self,
        test_logger: Logger,
        fake_session: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """After multiple syncs, fetch_venue_time is called each time."""
        ts = FakeTimeSync(
            venue=Venue.BYBIT,
            logger=test_logger,
            server_time_ms=5000,
        )
        monkeypatch.setattr(
            "framework.base.trading.time_sync.time_ns",
            lambda: 1_000_000_000,
        )
        await ts.start(fake_session)
        assert ts.fetch_call_count == 1

        await ts.sync()
        assert ts.fetch_call_count == 2

        ts.server_time_ms = 6000
        await ts.sync()
        assert ts.fetch_call_count == 3

    @pytest.mark.asyncio
    async def test_sync_raises_without_session(self, test_logger: Logger) -> None:
        """Calling sync() before start() must raise RuntimeError."""
        ts = FakeTimeSync(venue=Venue.BYBIT, logger=test_logger)

        with pytest.raises(RuntimeError, match="Session not set"):
            await ts.sync()

    @pytest.mark.asyncio
    async def test_sync_calls_fetch_venue_time(
        self,
        test_logger: Logger,
        fake_session: AsyncMock,
    ) -> None:
        """sync() must delegate to fetch_venue_time to obtain server time."""
        ts = FakeTimeSync(
            venue=Venue.BYBIT,
            logger=test_logger,
            server_time_ms=7000,
        )
        await ts.start(fake_session)

        assert ts.fetch_call_count == 1


class TestTimeSyncLifecycle:
    """Test start()/stop() and the background sync loop."""

    @pytest.mark.asyncio
    async def test_start_creates_background_task(
        self,
        test_logger: Logger,
        fake_session: AsyncMock,
    ) -> None:
        """start() must spawn an asyncio Task for the periodic loop."""
        ts = FakeTimeSync(venue=Venue.BYBIT, logger=test_logger)
        await ts.start(fake_session)

        assert ts._loop_task is not None
        assert ts.fetch_call_count == 1

    @pytest.mark.asyncio
    async def test_start_is_idempotent(
        self,
        test_logger: Logger,
        fake_session: AsyncMock,
    ) -> None:
        """Starting an active sync does not fetch again or leak another task."""
        ts = FakeTimeSync(venue=Venue.BYBIT, logger=test_logger)
        await ts.start(fake_session)
        loop_task = ts._loop_task

        await ts.start(fake_session)

        assert ts._loop_task is loop_task
        assert ts.fetch_call_count == 1

    @pytest.mark.asyncio
    async def test_start_failure_resets_session(
        self,
        test_logger: Logger,
        fake_session: AsyncMock,
    ) -> None:
        """An initial fetch failure leaves the component safe to restart."""
        ts = FakeTimeSync(venue=Venue.BYBIT, logger=test_logger)

        async def failing_fetch(session: aiohttp.ClientSession) -> int:
            raise ConnectionError("network error")

        ts.fetch_venue_time = failing_fetch  # type: ignore[method-assign]

        with pytest.raises(ConnectionError, match="network error"):
            await ts.start(fake_session)

        assert ts._session is None
        assert ts._loop_task is None

    @pytest.mark.asyncio
    async def test_stop_cancels_background_task(
        self,
        test_logger: Logger,
        fake_session: AsyncMock,
    ) -> None:
        """stop() must cancel the background task and wait for it."""
        ts = FakeTimeSync(venue=Venue.BYBIT, logger=test_logger)
        await ts.start(fake_session)

        await ts.stop()

        assert ts._loop_task is None
        assert ts._session is None

    @pytest.mark.asyncio
    async def test_stop_idempotent(
        self,
        test_logger: Logger,
        fake_session: AsyncMock,
    ) -> None:
        """Calling stop() twice must not raise."""
        ts = FakeTimeSync(venue=Venue.BYBIT, logger=test_logger)
        await ts.start(fake_session)
        await ts.stop()

        await ts.stop()

        assert ts._loop_task is None

    @pytest.mark.asyncio
    async def test_loop_handles_errors_gracefully(
        self,
        test_logger: Logger,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The loop must log warnings and continue when sync() raises."""
        ts = FakeTimeSync(
            venue=Venue.BYBIT,
            logger=test_logger,
            server_time_ms=0,
            sync_interval_s=0.01,
        )

        monkeypatch.setattr(
            "framework.base.trading.time_sync.time_ns",
            lambda: 1_000_000_000,
        )

        call_count = 0

        async def intermittently_failing_fetch(session: aiohttp.ClientSession) -> int:
            nonlocal call_count
            call_count += 1
            if call_count in (2, 3):
                msg = "network error"
                raise ConnectionError(msg)
            return 5000

        ts.fetch_venue_time = intermittently_failing_fetch  # type: ignore[method-assign]

        await ts.start(AsyncMock(spec=aiohttp.ClientSession))
        async with asyncio.timeout(2.0):
            while call_count < 3:
                await asyncio.sleep(0)
        await ts.stop()

        assert call_count >= 3

    @pytest.mark.asyncio
    async def test_is_stale_after_sync(
        self,
        test_logger: Logger,
        fake_session: AsyncMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """is_stale must be False shortly after a successful sync."""
        ts = FakeTimeSync(
            venue=Venue.BYBIT,
            logger=test_logger,
            server_time_ms=5000,
            stale_threshold_s=60.0,
        )
        await ts.start(fake_session)

        monkeypatch.setattr(
            "framework.base.trading.time_sync.time_ns",
            lambda: 1_000_000_000,
        )

        monotonic_values = [1_000_000_000, 1_000_000_000, 62_000_000_001]
        mono_iter = iter(monotonic_values)

        def mono() -> int:
            return next(mono_iter)

        monkeypatch.setattr(
            "framework.base.trading.time_sync.time_monotonic_ns",
            mono,
        )

        await ts.sync()
        assert ts.is_stale is False

        assert ts.is_stale is True


class TestTimeSyncFakeErrors:
    """Test error propagation in fetch_venue_time."""

    @pytest.mark.asyncio
    async def test_sync_propagates_fetch_error(
        self,
        test_logger: Logger,
        fake_session: AsyncMock,
    ) -> None:
        """sync() must let fetch_venue_time exceptions propagate."""
        ts = FakeTimeSync(venue=Venue.BYBIT, logger=test_logger)
        await ts.start(fake_session)

        async def raise_error(session: aiohttp.ClientSession) -> int:
            msg = "connection refused"
            raise ConnectionError(msg)

        ts.fetch_venue_time = raise_error  # type: ignore[method-assign]

        with pytest.raises(ConnectionError, match="connection refused"):
            await ts.sync()

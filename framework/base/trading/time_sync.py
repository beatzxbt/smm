"""Time synchronization base class using time-based EMA.

Provides periodic server-time offset tracking via TimeExponentialMovingAverage
from mm_toolbox, shared by HTTP and WebSocket clients for accurate request signing.

Usage:
    Subclass TimeSync, implement fetch_venue_time(), inject into Exchange + clients.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import final

import aiohttp

from framework.base.common import Venue
from mm_toolbox.logging.standard import Logger
from mm_toolbox.moving_average import TimeExponentialMovingAverage
from mm_toolbox.time import time_ms, time_monotonic_ns, time_ns


class TimeSync(ABC):
    """Base class for exchange clock synchronization.

    Maintains a time-weighted exponential moving average of the offset between
    local wall-clock time and the exchange server time. A periodic background
    task fetches server time at a configurable interval and updates the EMA.
    The smoothed offset is exposed via the ``time_ms`` property.

    Attributes:
        venue (Venue): Venue identifier for diagnostics.
        time_ms (int): Synced unix time in milliseconds (wall-clock + smoothed offset).
        offset_ms (int): Current smoothed offset in milliseconds.
        is_stale (bool): True if the last sync exceeds the staleness threshold.
    """

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        half_life_s: float = 120.0,
        sync_interval_s: float = 60.0,
        stale_threshold_s: float = 180.0,
    ) -> None:
        """Initialize the time sync component.

        Args:
            venue (Venue): Venue identifier for diagnostics.
            logger (Logger): Logger for sync status and error output.
            half_life_s (float): Time in seconds for the EMA weight to halve.
            sync_interval_s (float): Interval between periodic server-time fetches.
            stale_threshold_s (float): Duration after which the offset is considered stale.
        """
        self._venue = venue
        self._logger = logger
        self._sync_interval_s = sync_interval_s
        self._stale_threshold_s = stale_threshold_s
        self._last_synced_ns: int = 0

        self._tema = TimeExponentialMovingAverage(is_fast=True, half_life_s=half_life_s)

        self._session: aiohttp.ClientSession | None = None
        self._loop_task: asyncio.Task[None] | None = None
        self._lifecycle_lock = asyncio.Lock()

    @property
    def venue(self) -> Venue:
        """Venue identifier for diagnostics."""
        return self._venue

    @property
    def time_ms(self) -> int:
        """Synced unix time in milliseconds.

        Returns raw wall-clock time before the first sync (offset defaults to 0).
        """
        return time_ms() + int(self._tema.get_value())

    @property
    def offset_ms(self) -> int:
        """Current smoothed offset from local wall-clock to server time, in milliseconds."""
        return int(self._tema.get_value())

    @property
    def is_stale(self) -> bool:
        """True if never synced, or last sync exceeds the staleness threshold."""
        if self._last_synced_ns == 0:
            return True
        elapsed_s = (time_monotonic_ns() - self._last_synced_ns) / 1_000_000_000
        return elapsed_s > self._stale_threshold_s

    @final
    async def start(self, session: aiohttp.ClientSession) -> None:
        """Synchronize immediately, then begin periodic syncing.

        Args:
            session (aiohttp.ClientSession): Shared session for server-time requests.
        """
        async with self._lifecycle_lock:
            if self._loop_task is not None and not self._loop_task.done():
                return

            self._session = session
            try:
                await self.sync()
            except Exception:
                self._session = None
                raise
            self._loop_task = asyncio.create_task(self._loop())

    @final
    async def stop(self) -> None:
        """Cancel the background sync task. Idempotent."""
        async with self._lifecycle_lock:
            if self._loop_task is not None:
                self._loop_task.cancel()
                try:
                    await self._loop_task
                except asyncio.CancelledError:
                    pass
                self._loop_task = None
            self._session = None

    @final
    async def sync(self) -> None:
        """Fetch server time, compute raw offset, update the EMA.

        Raises:
            RuntimeError: If ``start()`` has not been called.
        """
        if self._session is None:
            raise RuntimeError("Session not set; call start() first")

        local_before_ns = time_ns()
        server_ms = await self.fetch_venue_time(self._session)
        local_after_ns = time_ns()

        local_avg_ms = (local_before_ns + local_after_ns) // 2_000_000
        raw_offset = server_ms - local_avg_ms

        self._tema.update(float(raw_offset))
        self._last_synced_ns = time_monotonic_ns()

    @abstractmethod
    async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
        """Query the exchange server-time endpoint.

        Args:
            session (aiohttp.ClientSession): Shared HTTP session for the request.

        Returns:
            int: Server unix time in milliseconds.
        """
        ...

    async def _loop(self) -> None:
        """Periodic sync loop. Logs fetch errors and continues."""
        while True:
            try:
                await asyncio.sleep(self._sync_interval_s)
                await self.sync()
            except asyncio.CancelledError:
                return
            except Exception as e:
                self._logger.warning(f"Time sync loop error for {self._venue}; {e}")

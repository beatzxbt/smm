"""Binance server-time synchronization."""

from __future__ import annotations

import aiohttp

from framework.base.common import Venue
from framework.base.trading.time_sync import TimeSync
from mm_toolbox.logging.standard import Logger


class BinanceTimeSync(TimeSync):
    """Time sync for Binance Futures API."""

    _URLS = {
        Venue.BINANCE_USDM: "https://fapi.binance.com/fapi/v1/time",
        Venue.BINANCE_COINM: "https://dapi.binance.com/dapi/v1/time",
    }

    def __init__(
        self,
        venue: Venue,
        logger: Logger,
        url: str | None = None,
        half_life_s: float = 120.0,
        sync_interval_s: float = 60.0,
        stale_threshold_s: float = 180.0,
    ) -> None:
        super().__init__(
            venue=venue,
            logger=logger,
            half_life_s=half_life_s,
            sync_interval_s=sync_interval_s,
            stale_threshold_s=stale_threshold_s,
        )
        self._url = url or self._URLS[venue]

    async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
        async with session.get(self._url) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return int(data["serverTime"])

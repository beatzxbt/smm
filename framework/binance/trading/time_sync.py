"""Binance server-time synchronization."""

from __future__ import annotations

import aiohttp

from framework.base.common import Venue
from framework.base.trading.time_sync import TimeSync


class BinanceTimeSync(TimeSync):
    """Time sync for Binance Futures API."""

    _URLS = {
        Venue.BINANCE_USDM: "https://fapi.binance.com/fapi/v1/time",
        Venue.BINANCE_COINM: "https://dapi.binance.com/dapi/v1/time",
    }

    async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
        url = self._URLS[self._venue]
        async with session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return int(data["serverTime"])

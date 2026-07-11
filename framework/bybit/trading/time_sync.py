"""Bybit server-time synchronization."""

from __future__ import annotations

import aiohttp

from framework.base.trading.time_sync import TimeSync


class BybitTimeSync(TimeSync):
    """Time sync for Bybit V5 API."""

    _URL = "https://api.bybit.com/v5/market/time"

    async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
        async with session.get(self._URL) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return int(data["result"]["timeMs"])

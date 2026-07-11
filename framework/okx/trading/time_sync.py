"""OKX server-time synchronization."""

from __future__ import annotations

import aiohttp

from framework.base.trading.time_sync import TimeSync


class OkxTimeSync(TimeSync):
    """Time sync for OKX V5 API."""

    _URL = "https://www.okx.com/api/v5/public/time"

    async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
        async with session.get(self._URL) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return int(data["data"][0]["ts"])

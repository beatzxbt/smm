"""Venue-specific clock synchronization and signing tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any

import aiohttp
import pytest

from framework.base.common import Venue
from framework.base.trading.client import HttpMethod
from framework.base.trading.time_sync import TimeSync
from framework.binance.trading.exchange import BinanceExchange
from framework.binance.trading.time_sync import BinanceTimeSync
from framework.bybit.trading.exchange import BybitExchange
from framework.bybit.trading.time_sync import BybitTimeSync
from framework.okx.trading.client import OkxHttpClient
from framework.okx.trading.exchange import OkxExchange
from framework.okx.trading.time_sync import OkxTimeSync
from mm_toolbox.logging.standard import Logger


class FakeResponse:
    """Minimal aiohttp response context manager."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.status_checked = False

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        self.status_checked = True

    async def json(self) -> dict[str, Any]:
        return self.payload


class FakeSession:
    """Minimal session that records the requested server-time URL."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.response = FakeResponse(payload)
        self.requested_url = ""

    def get(self, url: str) -> FakeResponse:
        self.requested_url = url
        return self.response


class FixedTimeSync(TimeSync):
    """Clock with a deterministic synchronized timestamp for signing tests."""

    def __init__(self, venue: Venue, logger: Logger, timestamp_ms: int) -> None:
        super().__init__(venue=venue, logger=logger)
        self.timestamp_ms = timestamp_ms

    @property
    def time_ms(self) -> int:
        return self.timestamp_ms

    async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
        return self.timestamp_ms


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("time_sync", "venue", "payload", "expected_time", "expected_url"),
    [
        (
            BinanceTimeSync,
            Venue.BINANCE_USDM,
            {"serverTime": 1_700_000_000_123},
            1_700_000_000_123,
            "https://fapi.binance.com/fapi/v1/time",
        ),
        (
            BinanceTimeSync,
            Venue.BINANCE_COINM,
            {"serverTime": 1_700_000_000_234},
            1_700_000_000_234,
            "https://dapi.binance.com/dapi/v1/time",
        ),
        (
            BybitTimeSync,
            Venue.BYBIT,
            {"result": {"timeMs": "1700000000456"}},
            1_700_000_000_456,
            "https://api.bybit.com/v5/market/time",
        ),
        (
            OkxTimeSync,
            Venue.OKX,
            {"data": [{"ts": "1700000000789"}]},
            1_700_000_000_789,
            "https://www.okx.com/api/v5/public/time",
        ),
    ],
)
async def test_fetch_venue_time_parses_response(
    time_sync: type[TimeSync],
    venue: Venue,
    payload: dict[str, Any],
    expected_time: int,
    expected_url: str,
    test_logger: Logger,
) -> None:
    """Each venue adapter parses its public server-time response."""
    sync = time_sync(venue=venue, logger=test_logger)
    session = FakeSession(payload)

    result = await sync.fetch_venue_time(session)  # type: ignore[arg-type]

    assert result == expected_time
    assert session.requested_url == expected_url
    assert session.response.status_checked is True


@pytest.mark.parametrize(
    ("exchange_type", "extra_kwargs"),
    [
        (BinanceExchange, {"is_usd_margined": True}),
        (BybitExchange, {}),
        (OkxExchange, {}),
    ],
)
def test_exchange_clients_share_one_clock(
    exchange_type: type,
    extra_kwargs: dict[str, Any],
    test_logger: Logger,
) -> None:
    """Concrete exchanges inject one clock into both trading clients."""
    exchange = exchange_type(
        logger=test_logger,
        load_secrets=False,
        **extra_kwargs,
    )

    assert exchange.http_client.time_sync is exchange.time_sync
    assert exchange.ws_client.time_sync is exchange.time_sync


def test_okx_http_sign_preserves_synced_milliseconds(test_logger: Logger) -> None:
    """OKX HTTP signatures retain millisecond precision in ISO timestamps."""
    time_sync = FixedTimeSync(
        venue=Venue.OKX,
        logger=test_logger,
        timestamp_ms=1_700_000_000_123,
    )
    client = OkxHttpClient(
        logger=test_logger,
        time_sync=time_sync,
        load_secrets=False,
    )
    client.key = "key"
    client.secret = "secret"
    client.passphrase = "passphrase"

    headers = client.sign(HttpMethod.GET, "/api/v5/account/balance", {})
    timestamp = "2023-11-14T22:13:20.123Z"
    expected_signature = base64.b64encode(
        hmac.new(
            key=b"secret",
            msg=f"{timestamp}GET/api/v5/account/balance".encode(),
            digestmod=hashlib.sha256,
        ).digest()
    ).decode()

    assert headers["OK-ACCESS-TIMESTAMP"] == timestamp
    assert headers["OK-ACCESS-SIGN"] == expected_signature

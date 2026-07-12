"""Tests for framework.binance.trading.client clients."""

from __future__ import annotations

import hmac
import hashlib

import aiohttp
import msgspec
import pytest

from framework.base.common import Venue
from framework.base.trading.client import HttpMethod
from framework.base.trading.time_sync import TimeSync
from framework.binance.trading.client import BinanceHttpClient, BinanceWsClient
from framework.base.trading.models import ClientResponseFailure, ClientResponseTransport
from mm_toolbox.logging.standard import Logger


def dummy_time_sync() -> TimeSync:
    """Create a no-op TimeSync stub for client tests."""

    class _Dummy(TimeSync):
        async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
            return 0

    return _Dummy(venue=Venue.BINANCE_USDM, logger=Logger(name="test"))


class TestBinanceHttpClientSign:
    """Layer 1: Signing behavior."""

    def test_sign_includes_timestamp_and_signature(self, monkeypatch) -> None:
        """Test sign returns params with timestamp and signature.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """
        monkeypatch.setattr("framework.base.trading.time_sync.time_ms", lambda: 1000)
        client = BinanceHttpClient(
            logger=Logger(name="test"),
            time_sync=dummy_time_sync(),
            load_secrets=False,
            is_usd_margined=True,
        )
        client.secret = "secret"

        signed = client.sign(HttpMethod.GET, "/v1/order", {"symbol": "BTCUSDT"})
        query_string = "symbol=BTCUSDT&timestamp=1000"
        expected = hmac.new(
            key=b"secret", msg=query_string.encode("utf-8"), digestmod=hashlib.sha256
        ).hexdigest()

        assert signed["timestamp"] == 1000
        assert signed["signature"] == expected


class TestBinanceWsClientSubmit:
    """Layer 1: Submit guard behavior."""

    @pytest.mark.asyncio
    async def test_submit_without_running_fails(self) -> None:
        """Test submit returns failure when client is not running."""
        client = BinanceWsClient(
            logger=Logger(name="test"),
            time_sync=dummy_time_sync(),
            load_secrets=False,
        )
        resp = await client.submit(data={}, decoder=None)  # type: ignore[arg-type]

        assert isinstance(resp, ClientResponseFailure)
        assert resp.err_msg == "Client not initialized"
        assert resp.meta.transport == ClientResponseTransport.WS
        assert resp.meta.operation == "unknown"

    @pytest.mark.asyncio
    async def test_submit_without_active_connection_fails(self) -> None:
        """Test submit returns failure when no active connection exists."""
        client = BinanceWsClient(
            logger=Logger(name="test"),
            time_sync=dummy_time_sync(),
            load_secrets=False,
        )
        client.is_running = True
        client.is_active = False
        resp = await client.submit(data={}, decoder=None)  # type: ignore[arg-type]

        assert isinstance(resp, ClientResponseFailure)
        assert resp.err_msg == "No active connection"
        assert resp.meta.transport == ClientResponseTransport.WS
        assert resp.meta.operation == "unknown"

    @pytest.mark.asyncio
    async def test_submit_uses_synced_timestamp(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Active WebSocket requests use the shared synchronized clock."""
        monkeypatch.setattr("framework.base.trading.time_sync.time_ms", lambda: 1000)
        time_sync = dummy_time_sync()
        time_sync._tema.update(250.0)
        client = BinanceWsClient(
            logger=Logger(name="test"),
            time_sync=time_sync,
            load_secrets=False,
        )

        class FakeWebSocket:
            def __init__(self) -> None:
                self.payload: dict = {}

            async def send_bytes(self, data: bytes) -> None:
                self.payload = msgspec.json.decode(data)
                await client._handle_message(
                    {"id": self.payload["id"], "status": 200, "result": {"ok": True}}
                )

        ws = FakeWebSocket()
        client.is_running = True
        client.is_active = True
        client.ws = ws  # type: ignore[assignment]

        class IdentityDecoder:
            def decode(self, value: dict) -> dict:
                return value

        response = await client.submit(
            data={"method": "order.place"},
            decoder=IdentityDecoder(),  # type: ignore[arg-type]
        )

        assert response.is_successful
        assert ws.payload["params"]["timestamp"] == 1250
        assert "timestamp" not in ws.payload
        assert "signature" in ws.payload["params"]

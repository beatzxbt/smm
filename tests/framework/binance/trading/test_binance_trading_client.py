"""Tests for framework.binance.trading.client clients."""

from __future__ import annotations

import hmac
import hashlib

import pytest

from framework.base.trading.client import HttpMethod
from framework.binance.trading.client import BinanceHttpClient, BinanceWsClient
from framework.base.trading.models import ClientResponseFailure, ClientResponseTransport
from mm_toolbox.logging.standard import Logger


class TestBinanceHttpClientSign:
    """Layer 1: Signing behavior."""

    def test_sign_includes_timestamp_and_signature(self, monkeypatch) -> None:
        """Test sign returns params with timestamp and signature.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """
        monkeypatch.setattr("framework.binance.trading.client.time_ms", lambda: 1000)
        client = BinanceHttpClient(
            logger=Logger(name="test"),
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
        client = BinanceWsClient(logger=Logger(name="test"), load_secrets=False)
        resp = await client.submit(data={}, decoder=None)  # type: ignore[arg-type]

        assert isinstance(resp, ClientResponseFailure)
        assert resp.err_msg == "Client not initialized"
        assert resp.meta.transport == ClientResponseTransport.WS
        assert resp.meta.operation == "unknown"

    @pytest.mark.asyncio
    async def test_submit_without_active_connection_fails(self) -> None:
        """Test submit returns failure when no active connection exists."""
        client = BinanceWsClient(logger=Logger(name="test"), load_secrets=False)
        client.is_running = True
        client.is_active = False
        resp = await client.submit(data={}, decoder=None)  # type: ignore[arg-type]

        assert isinstance(resp, ClientResponseFailure)
        assert resp.err_msg == "No active connection"
        assert resp.meta.transport == ClientResponseTransport.WS
        assert resp.meta.operation == "unknown"

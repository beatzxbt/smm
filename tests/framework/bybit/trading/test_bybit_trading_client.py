"""Tests for framework.bybit.trading.client clients."""

from __future__ import annotations

import hmac
import hashlib

import aiohttp
import msgspec
import pytest

from framework.base.common import Venue

from framework.base.trading.client import HttpMethod
from framework.base.trading.time_sync import TimeSync
from framework.bybit.trading.client import (
    BybitHttpClient,
    BybitWsClient,
    RECV_WINDOW_MS,
)
from framework.base.trading.models import (
    ClientResponseFailure,
    ClientResponseSuccess,
    ClientResponseTransport,
)
from mm_toolbox.logging.standard import Logger


def dummy_time_sync() -> TimeSync:
    """Create a no-op TimeSync stub for client tests."""

    class _Dummy(TimeSync):
        async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
            return 0

    return _Dummy(venue=Venue.BYBIT, logger=Logger(name="test"))


class DummyResponse:
    """Async context manager response for HTTP client tests.

    Args:
        payload: Payload to encode as JSON bytes.
    """

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status = 200

    async def __aenter__(self):
        """Enter the async context manager.

        Returns:
            DummyResponse: Response instance.
        """
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Exit the async context manager.

        Args:
            exc_type: Exception type, if raised.
            exc: Exception instance, if raised.
            tb: Traceback, if raised.

        Returns:
            bool: False to propagate exceptions.
        """
        return False

    async def read(self) -> bytes:
        """Return encoded payload bytes.

        Returns:
            bytes: JSON-encoded payload.
        """
        return msgspec.json.encode(self._payload)

    def raise_for_status(self) -> None:
        """No-op status check for tests.

        : Always returns None.
        """
        return None


class DummySession:
    """Dummy aiohttp session for HTTP client tests.

    Args:
        payload: Response payload to return.
    """

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.closed = False

    def request(self, **_kwargs):
        """Return a dummy response context manager.

        Args:
            **_kwargs: Ignored request arguments.

        Returns:
            DummyResponse: Context manager yielding a response.
        """
        return DummyResponse(self._payload)


class TestBybitHttpClientSign:
    """Layer 1: Signing behavior."""

    def test_sign_headers(self, monkeypatch):
        """Test sign builds expected HMAC signature headers.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """
        monkeypatch.setattr("framework.base.trading.time_sync.time_ms", lambda: 1000)
        client = BybitHttpClient(
            logger=Logger(name="test"),
            time_sync=dummy_time_sync(),
            load_secrets=False,
            key="key",
            secret="secret",
        )

        headers = client.sign(HttpMethod.GET, "/v5/market/tickers", {})
        payload = ""
        signature = hmac.new(
            key=b"secret",
            msg=f"1000key{RECV_WINDOW_MS}{payload}".encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        assert headers["X-BAPI-TIMESTAMP"] == "1000"
        assert headers["X-BAPI-API-KEY"] == "key"
        assert headers["X-BAPI-SIGN"] == signature


class TestBybitHttpClientRequest:
    """Layer 2: Request response mapping."""

    @pytest.mark.asyncio
    async def test_request_success(self):
        """Test request returns ClientResponseSuccess on retCode 0."""
        client = BybitHttpClient(
            logger=Logger(name="test"),
            time_sync=dummy_time_sync(),
            load_secrets=False,
        )
        client._session = DummySession({"retCode": 0, "result": {"ok": True}})

        resp = await client.request(
            method=HttpMethod.GET,
            endpoint="/v5/market/tickers",
            params={},
            data={},
            sign=False,
            decoder=msgspec.json.Decoder(dict),
        )

        assert isinstance(resp, ClientResponseSuccess)
        assert resp.data["ok"] is True
        assert resp.meta.transport == ClientResponseTransport.HTTP
        assert resp.meta.operation == "/v5/market/tickers"

    @pytest.mark.asyncio
    async def test_request_failure_ret_code(self):
        """Test request returns ClientResponseFailure on non-zero retCode."""
        client = BybitHttpClient(
            logger=Logger(name="test"),
            time_sync=dummy_time_sync(),
            load_secrets=False,
        )
        client._session = DummySession({"retCode": 1001, "retMsg": "fail"})

        resp = await client.request(
            method=HttpMethod.GET,
            endpoint="/v5/market/tickers",
            params={},
            data={},
            sign=False,
            decoder=msgspec.json.Decoder(dict),
        )

        assert isinstance(resp, ClientResponseFailure)
        assert resp.err_no == 1001
        assert resp.meta.transport == ClientResponseTransport.HTTP
        assert resp.meta.operation == "/v5/market/tickers"


class TestBybitWsClientSubmit:
    """Layer 1: Submit guard behavior."""

    @pytest.mark.asyncio
    async def test_submit_without_connection_fails(self):
        """Test submit returns failure when no active connection exists."""
        client = BybitWsClient(
            logger=Logger(name="test"),
            time_sync=dummy_time_sync(),
            load_secrets=False,
        )
        resp = await client.submit(data={}, decoder=msgspec.json.Decoder(dict))

        assert isinstance(resp, ClientResponseFailure)
        assert resp.err_msg == "No active connection"

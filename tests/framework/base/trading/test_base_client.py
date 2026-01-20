"""Tests for framework.base.trading.client base client behaviors.

Coverage includes:
- HttpClient ensure_running logic
- Session lifecycle and close behavior
- WsClient close behavior
"""

from __future__ import annotations

import pytest

from framework.base.common import Venue
from framework.base.trading.client import HttpClient, HttpMethod, WsClient
from framework.base.trading.models import ClientResponseSuccess
from mm_toolbox.logging.standard import Logger


class DummyHttpClient(HttpClient):
    """Minimal HTTP client implementation for base tests.

    Args:
        logger: Logger instance.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(venue=Venue.BINANCE_USDM, logger=logger, load_secrets=False)

    def sign(self, method: HttpMethod, endpoint: str, body: dict) -> dict:
        """Return empty signature for tests.

        Args:
            method: HTTP method.
            endpoint: API endpoint.
            body: Request body.

        Returns:
            dict: Empty signature map.
        """
        return {}

    async def request(  # type: ignore[override]
        self,
        method: HttpMethod,
        endpoint: str,
        params: dict,
        data: dict,
        sign: bool,
        decoder,
    ):
        """Return an empty response for tests.

        Args:
            method: HTTP method.
            endpoint: API endpoint.
            params: Query parameters.
            data: Request body.
            sign: Whether to sign the request.
            decoder: Response decoder.

        Returns:
            ClientResponseSuccess: Empty success response.
        """
        return ClientResponseSuccess(data={})


class DummyWsClient(WsClient):
    """Minimal WebSocket client implementation for base tests.

    Args:
        logger: Logger instance.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(venue=Venue.BINANCE_USDM, logger=logger, load_secrets=False)

    async def authenticate(self, ws) -> bool:
        """Return True for authentication in tests.

        Args:
            ws: WebSocket connection.

        Returns:
            bool: True for success.
        """
        return True

    async def heartbeat(self):
        """No-op heartbeat for tests."""
        return None

    async def connect(self):
        """No-op connect for tests."""
        return None

    async def submit(self, data: dict, decoder):  # type: ignore[override]
        """Return empty response for tests.

        Args:
            data: Payload to submit.
            decoder: Response decoder.

        Returns:
            ClientResponseSuccess: Empty success response.
        """
        return ClientResponseSuccess(data={})


class TestHttpClientEnsureRunning:
    """Layer 1: HttpClient running checks."""

    def test_ensure_running_returns_true(self, test_logger: Logger) -> None:
        """Test ensure_running returns True for running client.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyHttpClient(logger=test_logger)
        assert client.ensure_running() is True

    def test_ensure_running_raises_when_stopped(self, test_logger: Logger) -> None:
        """Test ensure_running raises when client is stopped.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyHttpClient(logger=test_logger)
        client.is_running = False
        with pytest.raises(ConnectionError):
            client.ensure_running()

    def test_ensure_running_no_throw(self, test_logger: Logger) -> None:
        """Test ensure_running returns False without raising when throw_exc False.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyHttpClient(logger=test_logger)
        client.is_running = False
        assert client.ensure_running(throw_exc=False) is False


class TestHttpClientSession:
    """Layer 2: HttpClient session lifecycle."""

    @pytest.mark.asyncio
    async def test_session_is_cached(self, test_logger: Logger) -> None:
        """Test session property returns a cached session.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyHttpClient(logger=test_logger)
        session_first = client.session
        session_second = client.session

        assert session_first is session_second
        await client.close()

    @pytest.mark.asyncio
    async def test_close_marks_not_running(self, test_logger: Logger) -> None:
        """Test close marks client as not running and closes session.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyHttpClient(logger=test_logger)
        _ = client.session
        await client.close()

        assert client.is_running is False


class TestWsClientClose:
    """Layer 2: WsClient close behavior."""

    @pytest.mark.asyncio
    async def test_close_marks_not_running(self, test_logger: Logger) -> None:
        """Test close marks WsClient as not running.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyWsClient(logger=test_logger)
        client.is_running = True
        await client.close()

        assert client.is_running is False

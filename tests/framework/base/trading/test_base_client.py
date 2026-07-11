"""Tests for framework.base.trading.client base client behaviors.

Coverage includes:
- HttpClient ensure_running logic
- Session lifecycle and close behavior
- WsClient close behavior
"""

from __future__ import annotations

import aiohttp
import pytest

from framework.base.common import Venue
from framework.base.trading.client import HttpClient, HttpMethod, WsClient
from framework.base.trading.time_sync import TimeSync
from framework.base.trading.models import (
    ClientResponseFailure,
    ClientResponseMeta,
    ClientResponseSuccess,
    ClientResponseTransport,
)
from mm_toolbox.logging.standard import Logger


def _dummy_time_sync() -> TimeSync:
    """Create a no-op TimeSync stub for client tests."""

    class _Dummy(TimeSync):
        async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
            return 0

    return _Dummy(venue=Venue.BINANCE_USDM, logger=Logger(name="test"))


class DummyHttpClient(HttpClient):
    """Minimal HTTP client implementation for base tests.

    Args:
        logger: Logger instance.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(
            venue=Venue.BINANCE_USDM,
            logger=logger,
            load_secrets=False,
            time_sync=_dummy_time_sync(),
        )

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
        super().__init__(
            venue=Venue.BINANCE_USDM,
            logger=logger,
            load_secrets=False,
            time_sync=_dummy_time_sync(),
        )

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
    """HttpClient running checks."""

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
    """HttpClient session lifecycle."""

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
    """WsClient close behavior."""

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


class TestHttpClientResponseHelpers:
    """HttpClient response helper methods."""

    def test_make_meta_defaults_finished_ns(self, test_logger: Logger) -> None:
        """Test make_meta defaults finished_ns to started_ns.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyHttpClient(logger=test_logger)
        meta = client.make_meta(
            transport=ClientResponseTransport.HTTP,
            operation="/v1/test",
            started_ns=100,
        )

        assert meta.started_ns == 100
        assert meta.finished_ns == 100
        assert meta.venue == Venue.BINANCE_USDM
        assert meta.transport == ClientResponseTransport.HTTP
        assert meta.operation == "/v1/test"

    def test_make_meta_propagates_optional_fields(self, test_logger: Logger) -> None:
        """Test make_meta propagates optional metadata fields.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyHttpClient(logger=test_logger)
        meta = client.make_meta(
            transport=ClientResponseTransport.HTTP,
            operation="/v1/test",
            started_ns=100,
            finished_ns=200,
            request_id="abc",
            status_code=418,
            attempt=2,
            timeout=True,
        )

        assert meta.finished_ns == 200
        assert meta.request_id == "abc"
        assert meta.status_code == 418
        assert meta.attempt == 2
        assert meta.timeout is True

    def test_make_success_attaches_meta(self, test_logger: Logger) -> None:
        """Test make_success returns success response with provided metadata.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyHttpClient(logger=test_logger)
        meta = ClientResponseMeta.immediate(
            venue=client.venue,
            transport=ClientResponseTransport.HTTP,
            operation="/v1/test",
        )

        response = client.make_success(data={"ok": True}, meta=meta)

        assert isinstance(response, ClientResponseSuccess)
        assert response.data == {"ok": True}
        assert response.meta == meta

    def test_make_failure_normalizes_blank_error(self, test_logger: Logger) -> None:
        """Test make_failure normalizes blank error details.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyHttpClient(logger=test_logger)
        meta = client.make_meta(
            transport=ClientResponseTransport.HTTP,
            operation="/v1/test",
            started_ns=100,
        )

        response = client.make_failure(meta=meta, err_no=0, err_msg="")

        assert isinstance(response, ClientResponseFailure)
        assert response.err_no == 1
        assert response.err_msg == "Unknown error"
        assert response.meta == meta

    def test_make_failure_preserves_error_details(self, test_logger: Logger) -> None:
        """Test make_failure preserves provided error details.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyHttpClient(logger=test_logger)
        meta = client.make_meta(
            transport=ClientResponseTransport.HTTP,
            operation="/v1/test",
            started_ns=100,
        )

        response = client.make_failure(meta=meta, err_no=123, err_msg="bad")

        assert isinstance(response, ClientResponseFailure)
        assert response.err_no == 123
        assert response.err_msg == "bad"


class TestWsClientResponseHelpers:
    """WsClient response helper methods."""

    def test_make_meta_defaults_finished_ns(self, test_logger: Logger) -> None:
        """Test make_meta defaults finished_ns to started_ns.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyWsClient(logger=test_logger)
        meta = client.make_meta(
            transport=ClientResponseTransport.WS,
            operation="op.test",
            started_ns=100,
        )

        assert meta.started_ns == 100
        assert meta.finished_ns == 100
        assert meta.venue == Venue.BINANCE_USDM
        assert meta.transport == ClientResponseTransport.WS
        assert meta.operation == "op.test"

    def test_make_failure_normalizes_blank_error(self, test_logger: Logger) -> None:
        """Test make_failure normalizes blank error details.

        Args:
            test_logger: Logger fixture for the client.
        """
        client = DummyWsClient(logger=test_logger)
        meta = client.make_meta(
            transport=ClientResponseTransport.WS,
            operation="op.test",
            started_ns=100,
        )

        response = client.make_failure(meta=meta, err_no=0, err_msg="")

        assert isinstance(response, ClientResponseFailure)
        assert response.err_no == 1
        assert response.err_msg == "Unknown error"
        assert response.meta == meta

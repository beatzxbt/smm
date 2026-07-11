"""Tests for framework.base.trading.exchange.Exchange utilities.

Coverage includes:
- Secret loading guards
- Running state checks
- Client session lifecycle
- Client order ID generation
"""

from __future__ import annotations

import pytest

import aiohttp

from framework.base.common import Instrument, InstrumentCollection, Venue
from framework.base.schema import Moments, MessageId
from framework.base.trading.client import HttpClient, HttpMethod, WsClient
from framework.base.trading.exchange import AllowedOrderIdChars, Exchange
from framework.base.trading.time_sync import TimeSync
from framework.base.trading.models import (
    AmendOrder,
    AmendOrderResponse,
    CancelAllOrders,
    CancelAllOrdersResponse,
    CancelOrder,
    CancelOrderResponse,
    ClientResponseFailure,
    ClientResponseMeta,
    ClientResponseSuccess,
    ClientResponseTransport,
    CreateOrder,
    CreateOrderResponse,
)
from mm_toolbox.logging.standard import Logger
from mm_toolbox.time import time_ms


class DummyTimeSync(TimeSync):
    """TimeSync stub for Exchange tests that only use Exchange utilities."""

    async def fetch_venue_time(self, session: aiohttp.ClientSession) -> int:
        return time_ms()


class DummyHttpClient(HttpClient):
    """Minimal HTTP client stub for Exchange tests.

    Args:
        logger: Logger instance for the client.
    """

    def __init__(self, logger: Logger, time_sync: TimeSync) -> None:
        super().__init__(
            venue=Venue.BINANCE_USDM,
            logger=logger,
            load_secrets=False,
            time_sync=time_sync,
        )
        self.is_running = True

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
            sign: Whether signing is requested.
            decoder: Decoder for response data.

        Returns:
            ClientResponseSuccess: Empty success response.
        """
        return ClientResponseSuccess(data={})


class DummyWsClient(WsClient):
    """Minimal WebSocket client stub for Exchange tests.

    Args:
        logger: Logger instance for the client.
    """

    def __init__(self, logger: Logger, time_sync: TimeSync) -> None:
        super().__init__(
            venue=Venue.BINANCE_USDM,
            logger=logger,
            load_secrets=False,
            time_sync=time_sync,
        )
        self.is_running = True

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
            decoder: Decoder for response data.

        Returns:
            ClientResponseSuccess: Empty success response.
        """
        return ClientResponseSuccess(data={})


class DummyExchange(Exchange):
    """Concrete Exchange implementation for testing base behavior.

    Args:
        logger: Logger instance.
    """

    def __init__(self, logger: Logger) -> None:
        time_sync = DummyTimeSync(venue=Venue.BINANCE_USDM, logger=logger)
        super().__init__(
            venue=Venue.BINANCE_USDM,
            logger=logger,
            load_secrets=False,
            http_client=DummyHttpClient(logger=logger, time_sync=time_sync),
            ws_client=DummyWsClient(logger=logger, time_sync=time_sync),
            time_sync=time_sync,
        )

    async def get_instrument_collection(self):
        """Return empty instrument collection for tests.

        Returns:
            ClientResponseSuccess: Empty collection.
        """
        return ClientResponseSuccess(data=InstrumentCollection([]))

    async def create_order(self, create_order: CreateOrder):
        """Return empty create order response for tests.

        Args:
            create_order: Create order trigger.

        Returns:
            ClientResponseSuccess: Empty response.
        """
        moments = Moments()
        response_id = MessageId(recv_time_ns=moments.recv_time_ns)
        return ClientResponseSuccess(
            data=CreateOrderResponse(
                id=response_id,
                origin_id=create_order.origin_id or create_order.id,
                moments=moments,
                instrument=create_order.instrument,
            )
        )

    async def amend_order(self, amend_order: AmendOrder):
        """Return empty amend order response for tests.

        Args:
            amend_order: Amend order trigger.

        Returns:
            ClientResponseSuccess: Empty response.
        """
        moments = Moments()
        response_id = MessageId(recv_time_ns=moments.recv_time_ns)
        return ClientResponseSuccess(
            data=AmendOrderResponse(
                id=response_id,
                origin_id=amend_order.origin_id or amend_order.id,
                moments=moments,
                instrument=amend_order.instrument,
            )
        )

    async def cancel_order(self, cancel_order: CancelOrder):
        """Return empty cancel order response for tests.

        Args:
            cancel_order: Cancel order trigger.

        Returns:
            ClientResponseSuccess: Empty response.
        """
        moments = Moments()
        response_id = MessageId(recv_time_ns=moments.recv_time_ns)
        return ClientResponseSuccess(
            data=CancelOrderResponse(
                id=response_id,
                origin_id=cancel_order.origin_id or cancel_order.id,
                moments=moments,
                instrument=cancel_order.instrument,
            )
        )

    async def cancel_all_orders(self, cancel_all_orders: CancelAllOrders):
        """Return empty cancel-all response for tests.

        Args:
            cancel_all_orders: Cancel-all trigger.

        Returns:
            ClientResponseSuccess: Empty response.
        """
        moments = Moments()
        response_id = MessageId(recv_time_ns=moments.recv_time_ns)
        return ClientResponseSuccess(
            data=CancelAllOrdersResponse(
                id=response_id,
                origin_id=cancel_all_orders.origin_id or cancel_all_orders.id,
                moments=moments,
                instrument=cancel_all_orders.instrument,
            )
        )

    async def get_trades(self, instruments: list[Instrument]):
        """Return failure response for tests.

        Args:
            instruments: Instruments list.

        Returns:
            ClientResponseFailure: Failure response.
        """
        return ClientResponseFailure(err_msg="not implemented")

    async def get_orderbook(self, instruments: list[Instrument]):
        """Return failure response for tests.

        Args:
            instruments: Instruments list.

        Returns:
            ClientResponseFailure: Failure response.
        """
        return ClientResponseFailure(err_msg="not implemented")

    async def get_ticker(self, instruments: list[Instrument]):
        """Return failure response for tests.

        Args:
            instruments: Instruments list.

        Returns:
            ClientResponseFailure: Failure response.
        """
        return ClientResponseFailure(err_msg="not implemented")

    async def get_instrument_info(self, instruments: list[Instrument]):
        """Return failure response for tests.

        Args:
            instruments: Instruments list.

        Returns:
            ClientResponseFailure: Failure response.
        """
        return ClientResponseFailure(err_msg="not implemented")

    async def get_orders(self, instruments: list[Instrument]):
        """Return failure response for tests.

        Args:
            instruments: Instruments list.

        Returns:
            ClientResponseFailure: Failure response.
        """
        return ClientResponseFailure(err_msg="not implemented")

    async def get_position(self, instruments: list[Instrument]):
        """Return failure response for tests.

        Args:
            instruments: Instruments list.

        Returns:
            ClientResponseFailure: Failure response.
        """
        return ClientResponseFailure(err_msg="not implemented")

    async def get_executions(self, instruments: list[Instrument]):
        """Return failure response for tests.

        Args:
            instruments: Instruments list.

        Returns:
            ClientResponseFailure: Failure response.
        """
        return ClientResponseFailure(err_msg="not implemented")

    async def get_account(self):
        """Return failure response for tests.

        Returns:
            ClientResponseFailure: Failure response.
        """
        return ClientResponseFailure(err_msg="not implemented")


class TestExchangeGuards:
    """Guard helpers."""

    def test_ensure_secrets_loaded_raises(self, test_logger: Logger) -> None:
        """Test ensure_secrets_loaded raises when secrets are disabled.

        Args:
            test_logger: Logger fixture for the exchange.
        """
        exchange = DummyExchange(logger=test_logger)
        with pytest.raises(RuntimeError, match="Required secrets"):
            exchange.ensure_secrets_loaded()

    def test_ensure_running_checks_clients(self, test_logger: Logger) -> None:
        """Test ensure_running raises when clients are not running.

        Args:
            test_logger: Logger fixture for the exchange.
        """
        exchange = DummyExchange(logger=test_logger)
        exchange.http_client.is_running = False
        exchange.ws_client.is_running = False

        with pytest.raises(RuntimeError):
            exchange.ensure_running()

        exchange.http_client.is_running = True
        with pytest.raises(RuntimeError):
            exchange.ensure_running()

        exchange.ws_client.is_running = True
        assert exchange.ensure_running() is True
        assert exchange.ensure_running(http_only=True) is True
        assert exchange.ensure_running(ws_only=True) is True


class TestExchangeSessions:
    """Session lifecycle behavior."""

    @pytest.mark.asyncio
    async def test_unauth_session_is_cached(self, test_logger: Logger) -> None:
        """Test unauth_session is created lazily and cached.

        Args:
            test_logger: Logger fixture for the exchange.
        """
        exchange = DummyExchange(logger=test_logger)
        session_first = exchange.unauth_session
        session_second = exchange.unauth_session

        assert session_first is session_second
        await exchange.close_clients()

    @pytest.mark.asyncio
    async def test_close_clients_resets_session(self, test_logger: Logger) -> None:
        """Test close_clients closes sessions and resets state.

        Args:
            test_logger: Logger fixture for the exchange.
        """
        exchange = DummyExchange(logger=test_logger)
        _ = exchange.unauth_session
        await exchange.close_clients()

        assert exchange._unauthenticated_session is None

    def test_exchange_and_clients_share_time_sync(self, test_logger: Logger) -> None:
        """Exchange and both clients use the same synchronized clock."""
        exchange = DummyExchange(logger=test_logger)

        assert exchange.http_client.time_sync is exchange.time_sync
        assert exchange.ws_client.time_sync is exchange.time_sync

    @pytest.mark.asyncio
    async def test_connect_syncs_before_websocket_connect(
        self,
        test_logger: Logger,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Connecting the trading WebSocket starts an initial time sync first."""
        exchange = DummyExchange(logger=test_logger)
        calls: list[str] = []

        async def sync_time() -> None:
            calls.append("sync")

        async def connect() -> None:
            calls.append("connect")

        monkeypatch.setattr(exchange, "sync_time", sync_time)
        monkeypatch.setattr(exchange.ws_client, "connect", connect)

        await exchange.connect_ws_client()

        assert calls == ["sync", "connect"]


class TestExchangeCloid:
    """Client order ID generation."""

    def test_generate_cloid_with_padding(
        self, monkeypatch, test_logger: Logger
    ) -> None:
        """Test generate_cloid pads when timestamp is short.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
            test_logger: Logger fixture for the exchange.
        """
        monkeypatch.setattr(
            "framework.base.trading.exchange.time_monotonic_ns", lambda: 123
        )
        exchange = DummyExchange(logger=test_logger)
        exchange.max_cloid_length = 6

        cloid = exchange.generate_cloid()
        assert cloid == "000123"

    def test_generate_cloid_with_prefix_suffix(
        self, monkeypatch, test_logger: Logger
    ) -> None:
        """Test generate_cloid includes prefix and suffix.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
            test_logger: Logger fixture for the exchange.
        """
        monkeypatch.setattr(
            "framework.base.trading.exchange.time_monotonic_ns", lambda: 123456
        )
        exchange = DummyExchange(logger=test_logger)
        exchange.max_cloid_length = 10

        cloid = exchange.generate_cloid(prefix="AA", suffix="ZZ")
        assert cloid.startswith("AA")
        assert cloid.endswith("ZZ")
        assert len(cloid) == 10

    def test_generate_cloid_raises_on_invalid_length(self, test_logger: Logger) -> None:
        """Test generate_cloid raises when prefix+suffix exceed max length.

        Args:
            test_logger: Logger fixture for the exchange.
        """
        exchange = DummyExchange(logger=test_logger)
        exchange.max_cloid_length = 4

        with pytest.raises(ValueError, match="Invalid cloid length"):
            exchange.generate_cloid(prefix="AB", suffix="CD")

    def test_generate_cloid_returns_client_order_id(
        self, monkeypatch, test_logger: Logger
    ) -> None:
        """Test generate_cloid returns a ClientOrderId typed value.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
            test_logger: Logger fixture for the exchange.
        """
        monkeypatch.setattr(
            "framework.base.trading.exchange.time_monotonic_ns", lambda: 123
        )
        exchange = DummyExchange(logger=test_logger)

        cloid = exchange.generate_cloid()
        assert isinstance(cloid, str)
        assert cloid == "000000000000000000000000000000000123"

    def test_generate_cloid_numeric_raises_on_string_prefix(
        self, monkeypatch, test_logger: Logger
    ) -> None:
        """Test generate_cloid with NUMERIC chars raises on string prefix.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
            test_logger: Logger fixture for the exchange.
        """
        monkeypatch.setattr(
            "framework.base.trading.exchange.time_monotonic_ns", lambda: 123
        )
        exchange = DummyExchange(logger=test_logger)
        exchange.allowed_cloid_chars = AllowedOrderIdChars.NUMERIC

        with pytest.raises(ValueError, match="must be integers"):
            exchange.generate_cloid(prefix="ABC")

    def test_generate_cloid_numeric_accepts_int_affixes(
        self, monkeypatch, test_logger: Logger
    ) -> None:
        """Test generate_cloid with NUMERIC chars accepts integer prefix/suffix.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
            test_logger: Logger fixture for the exchange.
        """
        monkeypatch.setattr(
            "framework.base.trading.exchange.time_monotonic_ns", lambda: 12345
        )
        exchange = DummyExchange(logger=test_logger)
        exchange.allowed_cloid_chars = AllowedOrderIdChars.NUMERIC
        exchange.max_cloid_length = 12

        cloid = exchange.generate_cloid(prefix=99, suffix=1)
        assert cloid.startswith("99")
        assert cloid.endswith("1")

    def test_generate_cloid_alphabetic_raises_on_int_prefix(
        self, monkeypatch, test_logger: Logger
    ) -> None:
        """Test generate_cloid with ALPHABETIC chars raises on int prefix.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
            test_logger: Logger fixture for the exchange.
        """
        monkeypatch.setattr(
            "framework.base.trading.exchange.time_monotonic_ns", lambda: 123
        )
        exchange = DummyExchange(logger=test_logger)
        exchange.allowed_cloid_chars = AllowedOrderIdChars.ALPHABETIC

        with pytest.raises(ValueError, match="must be strings"):
            exchange.generate_cloid(prefix=123)

    def test_generate_cloid_truncates_long_timestamp(
        self, monkeypatch, test_logger: Logger
    ) -> None:
        """Test generate_cloid left-truncates timestamp when longer than available space.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
            test_logger: Logger fixture for the exchange.
        """
        monkeypatch.setattr(
            "framework.base.trading.exchange.time_monotonic_ns",
            lambda: 12345678901234567890,
        )
        exchange = DummyExchange(logger=test_logger)
        exchange.max_cloid_length = 10

        cloid = exchange.generate_cloid(prefix="A", suffix="Z")
        assert len(cloid) == 10
        assert cloid.startswith("A")
        assert cloid.endswith("Z")
        assert cloid[1:-1].isdigit()


class TestExchangeResponseHelpers:
    """Exchange response helper methods."""

    def test_make_meta_defaults_finished_ns(self, test_logger: Logger) -> None:
        """Test make_meta defaults finished_ns to started_ns.

        Args:
            test_logger: Logger fixture for the exchange.
        """
        exchange = DummyExchange(logger=test_logger)
        meta = exchange.make_meta(
            operation="exchange.test",
            started_ns=100,
        )

        assert meta.started_ns == 100
        assert meta.finished_ns == 100
        assert meta.venue == Venue.BINANCE_USDM
        assert meta.transport == ClientResponseTransport.INTERNAL
        assert meta.operation == "exchange.test"

    def test_make_meta_propagates_optional_fields(self, test_logger: Logger) -> None:
        """Test make_meta propagates optional metadata fields.

        Args:
            test_logger: Logger fixture for the exchange.
        """
        exchange = DummyExchange(logger=test_logger)
        meta = exchange.make_meta(
            operation="exchange.test",
            started_ns=100,
            finished_ns=200,
            request_id="abc",
            status_code=500,
            attempt=3,
            timeout=True,
        )

        assert meta.finished_ns == 200
        assert meta.request_id == "abc"
        assert meta.status_code == 500
        assert meta.attempt == 3
        assert meta.timeout is True

    def test_make_success_attaches_meta(self, test_logger: Logger) -> None:
        """Test make_success returns success response with provided metadata.

        Args:
            test_logger: Logger fixture for the exchange.
        """
        exchange = DummyExchange(logger=test_logger)
        meta = ClientResponseMeta.immediate(
            venue=exchange.venue,
            transport=ClientResponseTransport.INTERNAL,
            operation="exchange.test",
        )

        response = exchange.make_success(data={"ok": True}, meta=meta)

        assert isinstance(response, ClientResponseSuccess)
        assert response.data == {"ok": True}
        assert response.meta == meta

    def test_make_failure_normalizes_blank_error(self, test_logger: Logger) -> None:
        """Test make_failure normalizes blank error details.

        Args:
            test_logger: Logger fixture for the exchange.
        """
        exchange = DummyExchange(logger=test_logger)
        meta = exchange.make_meta(
            operation="exchange.test",
            started_ns=100,
        )

        response = exchange.make_failure(meta=meta, err_no=0, err_msg="")

        assert isinstance(response, ClientResponseFailure)
        assert response.err_no == 1
        assert response.err_msg == "Unknown error"
        assert response.meta == meta

    def test_make_failure_preserves_error_details(self, test_logger: Logger) -> None:
        """Test make_failure preserves provided error details.

        Args:
            test_logger: Logger fixture for the exchange.
        """
        exchange = DummyExchange(logger=test_logger)
        meta = exchange.make_meta(
            operation="exchange.test",
            started_ns=100,
        )

        response = exchange.make_failure(meta=meta, err_no=7, err_msg="bad")

        assert isinstance(response, ClientResponseFailure)
        assert response.err_no == 7
        assert response.err_msg == "bad"

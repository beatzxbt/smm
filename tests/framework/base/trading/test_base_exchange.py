"""Tests for framework.base.trading.exchange.Exchange utilities.

Coverage includes:
- Secret loading guards
- Running state checks
- Client session lifecycle
- Client order ID generation
"""

from __future__ import annotations

import pytest

from framework.base.common import Instrument, InstrumentCollection, Venue
from framework.base.trading.client import HttpClient, HttpMethod, WsClient
from framework.base.trading.exchange import Exchange
from framework.base.trading.models import (
    AmendOrder,
    AmendOrderResponse,
    CancelAllOrders,
    CancelAllOrdersResponse,
    CancelOrder,
    CancelOrderResponse,
    ClientResponseFailure,
    ClientResponseSuccess,
    CreateOrder,
    CreateOrderResponse,
)
from mm_toolbox.logging.standard import Logger


class DummyHttpClient(HttpClient):
    """Minimal HTTP client stub for Exchange tests.

    Args:
        logger: Logger instance for the client.
    """

    def __init__(self, logger: Logger) -> None:
        super().__init__(venue=Venue.BINANCE_USDM, logger=logger, load_secrets=False)
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

    def __init__(self, logger: Logger) -> None:
        super().__init__(venue=Venue.BINANCE_USDM, logger=logger, load_secrets=False)
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
        super().__init__(
            venue=Venue.BINANCE_USDM,
            logger=logger,
            load_secrets=False,
            http_client=DummyHttpClient(logger=logger),
            ws_client=DummyWsClient(logger=logger),
        )

    async def get_instrument_collection(self):
        """Return empty instrument collection for tests.

        Returns:
            ClientResponseSuccess: Empty collection.
        """
        return ClientResponseSuccess(data=InstrumentCollection())

    async def create_order(self, create_order: CreateOrder):
        """Return empty create order response for tests.

        Args:
            create_order: Create order trigger.

        Returns:
            ClientResponseSuccess: Empty response.
        """
        return ClientResponseSuccess(
            data=CreateOrderResponse(
                moments=None,  # type: ignore[arg-type]
                venue=self.venue,
                instrument=create_order.instrument,
                trigger=create_order,
            )
        )

    async def amend_order(self, amend_order: AmendOrder):
        """Return empty amend order response for tests.

        Args:
            amend_order: Amend order trigger.

        Returns:
            ClientResponseSuccess: Empty response.
        """
        return ClientResponseSuccess(
            data=AmendOrderResponse(
                moments=None,  # type: ignore[arg-type]
                venue=self.venue,
                instrument=amend_order.instrument,
                trigger=amend_order,
            )
        )

    async def cancel_order(self, cancel_order: CancelOrder):
        """Return empty cancel order response for tests.

        Args:
            cancel_order: Cancel order trigger.

        Returns:
            ClientResponseSuccess: Empty response.
        """
        return ClientResponseSuccess(
            data=CancelOrderResponse(
                moments=None,  # type: ignore[arg-type]
                venue=self.venue,
                instrument=cancel_order.instrument,
                trigger=cancel_order,
            )
        )

    async def cancel_all_orders(self, cancel_all_orders: CancelAllOrders):
        """Return empty cancel-all response for tests.

        Args:
            cancel_all_orders: Cancel-all trigger.

        Returns:
            ClientResponseSuccess: Empty response.
        """
        return ClientResponseSuccess(
            data=CancelAllOrdersResponse(
                moments=None,  # type: ignore[arg-type]
                venue=self.venue,
                instrument=cancel_all_orders.instrument,
                trigger=cancel_all_orders,
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
        monkeypatch.setattr("framework.base.trading.exchange.time_ns", lambda: 123)
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
        monkeypatch.setattr("framework.base.trading.exchange.time_ns", lambda: 123456)
        exchange = DummyExchange(logger=test_logger)
        exchange.max_cloid_length = 10

        cloid = exchange.generate_cloid(start="AA", end="ZZ")
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
            exchange.generate_cloid(start="AB", end="CD")

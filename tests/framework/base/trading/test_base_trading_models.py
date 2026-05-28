"""Tests for framework.base.trading.models module.

Tests cover:
- Order action structs (CreateOrder, AmendOrder, CancelOrder, CancelAllOrders)
- Secret struct for credential management
- Client response types (Success/Failure)
- Trading response structs (all *Response classes)
- Type unions (AnyOrderActionResponse, AnyClientResponse)

Tests are organized by dependency layer:
1. Primitives: CreateOrder, AmendOrder, CancelOrder, CancelAllOrders, Secret, ClientResponse
2. Composites: All *Response classes with EnvelopeSchema
"""

from __future__ import annotations

from typing import Any

import pytest

from framework.base.common import (
    Asset,
    ClientOrderId,
    Instrument,
    InstrumentType,
    OrderId,
    Symbol,
    Venue,
)
from framework.base.schema import MessageId, Moments
from framework.base.stream.models import (
    Execution,
    Order,
    OrderbookLevel,
    OrderTimeInForce,
    Trade,
)
from framework.base.trading.models import (
    AccountResponse,
    AmendOrder,
    AmendOrderResponse,
    CancelAllOrders,
    CancelAllOrdersResponse,
    CancelOrder,
    CancelOrderResponse,
    ClientResponse,
    ClientResponseFailure,
    ClientResponseMeta,
    ClientResponseSuccess,
    ClientResponseTransport,
    CreateOrder,
    CreateOrderResponse,
    ExecutionResponse,
    InstrumentInfoResponse,
    OrderbookResponse,
    OrdersResponse,
    PositionResponse,
    Secret,
    TickerResponse,
    TradesResponse,
    is_success,
)


@pytest.fixture
def sample_instrument():
    """Reusable instrument for tests."""
    return Instrument(
        venue=Venue.BINANCE_USDM,
        base=Asset("BTC"),
        quote=Asset("USDT"),
        symbol=Symbol("BTCUSDT"),
        code=1,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )


@pytest.fixture
def sample_moments():
    """Reusable Moments for envelope-backed responses."""
    return Moments(exch_time_ns=1000, recv_time_ns=2000)


@pytest.fixture
def sample_message_id(sample_moments):
    """Reusable message identifier aligned with sample moments."""
    return MessageId(recv_time_ns=sample_moments.recv_time_ns)


@pytest.fixture
def envelope_kwargs(sample_instrument, sample_moments, sample_message_id):
    """Reusable envelope kwargs for trading responses."""
    return {
        "id": sample_message_id,
        "origin_id": sample_message_id,
        "moments": sample_moments,
        "instrument": sample_instrument,
    }


class TestCreateOrder:
    """Test CreateOrder validation."""

    def test_creation_with_valid_maker_order(self, sample_instrument):
        """Test creating valid maker order with price."""
        order = CreateOrder(
            instrument=sample_instrument,
            size=1.0,
            is_buy=True,
            price=100.0,
            is_maker=True,
            tif=OrderTimeInForce.PO,
            reduce_only=False,
            client_order_id=ClientOrderId("client123"),
        )

        assert order.size == 1.0
        assert order.is_buy is True
        assert order.price == 100.0
        assert order.is_maker is True
        assert order.tif == OrderTimeInForce.PO
        assert order.reduce_only is False
        assert order.client_order_id == "client123"
        assert order.origin_id == order.id

    def test_creation_with_valid_taker_order(self, sample_instrument):
        """Test creating valid taker order without price."""
        order = CreateOrder(
            instrument=sample_instrument,
            size=1.0,
            is_buy=False,
            price=None,
            is_maker=False,
            tif=OrderTimeInForce.IOC,
            reduce_only=True,
        )

        assert order.size == 1.0
        assert order.is_buy is False
        assert order.price is None
        assert order.is_maker is False
        assert order.reduce_only is True
        assert order.origin_id == order.id


class TestCreateOrderValidation:
    """Test CreateOrder __post_init__ validation."""

    def test_size_must_be_positive(self, sample_instrument):
        """Test size must be > 0."""
        with pytest.raises(ValueError, match="Size must be greater than 0"):
            CreateOrder(
                instrument=sample_instrument,
                size=0.0,
                is_buy=True,
                price=100.0,
                is_maker=True,
                tif=OrderTimeInForce.PO,
                reduce_only=False,
            )

    def test_price_must_be_positive_when_provided(self, sample_instrument):
        """Test price must be > 0 when provided."""
        with pytest.raises(ValueError, match="Price must be greater than 0"):
            CreateOrder(
                instrument=sample_instrument,
                size=1.0,
                is_buy=True,
                price=0.0,
                is_maker=True,
                tif=OrderTimeInForce.PO,
                reduce_only=False,
            )

    def test_maker_order_must_have_price(self, sample_instrument):
        """Test maker orders must have a price."""
        with pytest.raises(ValueError, match="Maker orders must have a price"):
            CreateOrder(
                instrument=sample_instrument,
                size=1.0,
                is_buy=True,
                price=None,
                is_maker=True,
                tif=OrderTimeInForce.PO,
                reduce_only=False,
            )

    def test_taker_order_cannot_be_post_only(self, sample_instrument):
        """Test taker orders cannot have PostOnly TIF."""
        with pytest.raises(ValueError, match="Taker orders cannot be PostOnly"):
            CreateOrder(
                instrument=sample_instrument,
                size=1.0,
                is_buy=True,
                price=100.0,
                is_maker=False,
                tif=OrderTimeInForce.PO,
                reduce_only=False,
            )

    @pytest.mark.parametrize(
        "size,price,is_maker,tif,should_raise",
        [
            # Invalid cases
            (0.0, 100.0, True, OrderTimeInForce.PO, True),  # size <= 0
            (-1.0, 100.0, True, OrderTimeInForce.PO, True),  # negative size
            (1.0, 0.0, True, OrderTimeInForce.PO, True),  # price <= 0
            (1.0, -1.0, True, OrderTimeInForce.PO, True),  # negative price
            (1.0, None, True, OrderTimeInForce.PO, True),  # maker without price
            (1.0, 100.0, False, OrderTimeInForce.PO, True),  # taker with PO
            # Valid cases
            (1.0, 100.0, True, OrderTimeInForce.PO, False),  # valid maker
            (1.0, None, False, OrderTimeInForce.IOC, False),  # valid taker
            (1.0, 100.0, True, OrderTimeInForce.GTC, False),  # maker with GTC
        ],
    )
    def test_validation_matrix(
        self, sample_instrument, size, price, is_maker, tif, should_raise
    ):
        """Test validation across multiple parameter combinations."""
        if should_raise:
            with pytest.raises(ValueError):
                CreateOrder(
                    instrument=sample_instrument,
                    size=size,
                    is_buy=True,
                    price=price,
                    is_maker=is_maker,
                    tif=tif,
                    reduce_only=False,
                )
        else:
            order = CreateOrder(
                instrument=sample_instrument,
                size=size,
                is_buy=True,
                price=price,
                is_maker=is_maker,
                tif=tif,
                reduce_only=False,
            )
            assert order.size == size


class TestAmendOrder:
    """Test AmendOrder validation."""

    def test_creation_with_order_id(self, sample_instrument):
        """Test creating AmendOrder with order_id."""
        order = AmendOrder(
            instrument=sample_instrument,
            size=2.0,
            price=101.0,
            order_id=OrderId("order123"),
            client_order_id=None,
        )

        assert order.size == 2.0
        assert order.price == 101.0
        assert order.order_id == "order123"
        assert order.client_order_id is None

    def test_creation_with_client_order_id(self, sample_instrument):
        """Test creating AmendOrder with client_order_id."""
        order = AmendOrder(
            instrument=sample_instrument,
            size=2.0,
            price=101.0,
            order_id=None,
            client_order_id=ClientOrderId("client123"),
        )

        assert order.client_order_id == "client123"
        assert order.order_id is None


class TestAmendOrderValidation:
    """Test AmendOrder __post_init__ validation."""

    def test_size_must_be_positive(self, sample_instrument):
        """Test size must be > 0."""
        with pytest.raises(ValueError, match="Size must be greater than 0"):
            AmendOrder(
                instrument=sample_instrument,
                size=0.0,
                price=100.0,
                order_id=OrderId("order123"),
            )

    def test_price_must_be_positive_when_provided(self, sample_instrument):
        """Test price must be > 0 when provided."""
        with pytest.raises(ValueError, match="Price must be greater than 0"):
            AmendOrder(
                instrument=sample_instrument,
                size=1.0,
                price=0.0,
                order_id=OrderId("order123"),
            )

    def test_must_have_order_id_or_client_order_id(self, sample_instrument):
        """Test must have at least one ID."""
        with pytest.raises(
            ValueError, match="order_id or client_order_id must be provided"
        ):
            AmendOrder(
                instrument=sample_instrument,
                size=1.0,
                price=100.0,
                order_id=None,
                client_order_id=None,
            )

    @pytest.mark.parametrize(
        "size,price,order_id,client_order_id,should_raise",
        [
            # Invalid cases
            (0.0, 100.0, "oid", None, True),  # size <= 0
            (1.0, 0.0, "oid", None, True),  # price <= 0
            (1.0, 100.0, None, None, True),  # no IDs
            # Valid cases
            (1.0, 100.0, "oid", None, False),  # with order_id
            (1.0, 100.0, None, "clid", False),  # with client_order_id
            (1.0, 100.0, "oid", "clid", False),  # with both IDs
            (1.0, None, "oid", None, False),  # without price (market amend)
        ],
    )
    def test_validation_matrix(
        self, sample_instrument, size, price, order_id, client_order_id, should_raise
    ):
        """Test validation across multiple parameter combinations."""
        typed_order_id = OrderId(str(order_id)) if order_id is not None else None
        typed_client_order_id = (
            ClientOrderId(str(client_order_id)) if client_order_id is not None else None
        )
        if should_raise:
            with pytest.raises(ValueError):
                AmendOrder(
                    instrument=sample_instrument,
                    size=size,
                    price=price,
                    order_id=typed_order_id,
                    client_order_id=typed_client_order_id,
                )
        else:
            order = AmendOrder(
                instrument=sample_instrument,
                size=size,
                price=price,
                order_id=typed_order_id,
                client_order_id=typed_client_order_id,
            )
            assert order.size == size


class TestCancelOrder:
    """Test CancelOrder validation."""

    def test_creation_with_order_id(self, sample_instrument):
        """Test creating CancelOrder with order_id."""
        order = CancelOrder(
            instrument=sample_instrument,
            order_id=OrderId("order123"),
            client_order_id=None,
        )

        assert order.order_id == "order123"
        assert order.client_order_id is None

    def test_creation_with_client_order_id(self, sample_instrument):
        """Test creating CancelOrder with client_order_id."""
        order = CancelOrder(
            instrument=sample_instrument,
            order_id=None,
            client_order_id=ClientOrderId("client123"),
        )

        assert order.order_id is None
        assert order.client_order_id == "client123"

    def test_must_have_order_id_or_client_order_id(self, sample_instrument):
        """Test must have at least one ID."""
        with pytest.raises(
            ValueError, match="Either order_id or client_order_id must be provided"
        ):
            CancelOrder(
                instrument=sample_instrument,
                order_id=None,
                client_order_id=None,
            )


class TestCancelAllOrders:
    """Test CancelAllOrders."""

    def test_creation_with_instrument_only(self, sample_instrument):
        """Test creating CancelAllOrders with just instrument."""
        order = CancelAllOrders(
            instrument=sample_instrument,
            order_ids=None,
            client_order_ids=None,
        )

        assert order.order_ids is None
        assert order.client_order_ids is None

    def test_creation_with_order_ids(self, sample_instrument):
        """Test creating CancelAllOrders with order_ids list."""
        order = CancelAllOrders(
            instrument=sample_instrument,
            order_ids=[OrderId("order1"), OrderId("order2")],
            client_order_ids=None,
        )

        assert order.order_ids == ["order1", "order2"]
        assert order.client_order_ids is None

    def test_creation_with_client_order_ids(self, sample_instrument):
        """Test creating CancelAllOrders with client_order_ids list."""
        order = CancelAllOrders(
            instrument=sample_instrument,
            order_ids=None,
            client_order_ids=[
                ClientOrderId("client1"),
                ClientOrderId("client2"),
            ],
        )

        assert order.order_ids is None
        assert order.client_order_ids == ["client1", "client2"]

    def test_creation_with_both_id_lists(self, sample_instrument):
        """Test creating CancelAllOrders with both ID lists."""
        order = CancelAllOrders(
            instrument=sample_instrument,
            order_ids=[OrderId("order1")],
            client_order_ids=[ClientOrderId("client1")],
        )

        assert order.order_ids == ["order1"]
        assert order.client_order_ids == ["client1"]


class TestSecret:
    """Test Secret struct."""

    def test_creation_with_name_and_value(self):
        """Test creating Secret with name and value."""
        secret = Secret(name="API_KEY", value="secret_value_123")

        assert secret.name == "API_KEY"
        assert secret.value == "secret_value_123"

    def test_frozen_immutability(self):
        """Test that Secret is immutable (frozen=True)."""
        secret = Secret(name="API_KEY", value="secret_value")

        with pytest.raises(AttributeError):
            secret.name = "NEW_KEY"  # type: ignore

    def test_blank_creation(self):
        """Test blank() classmethod."""
        secret = Secret.blank()

        assert secret.name == ""
        assert secret.value == ""

    def test_is_blank_true_for_blank_secret(self):
        """Test is_blank() returns True for blank secrets."""
        secret = Secret.blank()

        assert secret.is_blank() is True

    def test_is_blank_false_for_non_blank_secret(self):
        """Test is_blank() returns False for non-blank secrets."""
        secret = Secret(name="API_KEY", value="secret_value")

        assert secret.is_blank() is False

    def test_set_creation(self):
        """Test set() classmethod sets environment variable."""
        import os

        secret = Secret.set("TEST_VAR", "test_value")

        assert secret.name == "TEST_VAR"
        assert secret.value == "test_value"
        assert os.environ.get("TEST_VAR") == "test_value"

        # Cleanup
        del os.environ["TEST_VAR"]


class TestSecretLoading:
    """Test Secret loading from environment."""

    def test_load_existing_variable(self):
        """Test load() with existing environment variable."""
        import os

        os.environ["TEST_API_KEY"] = "secret123"

        secret = Secret.load("TEST_API_KEY")

        assert secret.name == "TEST_API_KEY"
        assert secret.value == "secret123"

        # Cleanup
        del os.environ["TEST_API_KEY"]

    def test_maybe_load_existing_variable(self):
        """Test maybe_load() with existing environment variable."""
        import os

        os.environ["TEST_MAYBE_API_KEY"] = "secret456"

        secret = Secret.maybe_load("TEST_MAYBE_API_KEY")

        assert secret.name == "TEST_MAYBE_API_KEY"
        assert secret.value == "secret456"
        assert secret.is_blank() is False

        # Cleanup
        del os.environ["TEST_MAYBE_API_KEY"]

    def test_load_missing_variable_raises(self):
        """Test load() raises for missing environment variable."""
        with pytest.raises(RuntimeError, match="Failed to load.*from '.env'"):
            Secret.load("NONEXISTENT_VARIABLE_XYZ")

    def test_maybe_load_missing_variable_returns_blank(self):
        """Test maybe_load() returns blank for missing environment variable."""
        secret = Secret.maybe_load("NONEXISTENT_VARIABLE_XYZ")

        assert secret.is_blank() is True

    def test_maybe_load_empty_variable_returns_blank(self):
        """Test maybe_load() returns blank for empty environment variable."""
        import os

        os.environ["TEST_EMPTY_SECRET"] = ""

        secret = Secret.maybe_load("TEST_EMPTY_SECRET")

        assert secret.is_blank() is True

        # Cleanup
        del os.environ["TEST_EMPTY_SECRET"]


class TestClientResponseSuccess:
    """Test ClientResponseSuccess."""

    def test_creation_with_data(self):
        """Test creating successful response with data."""
        resp = ClientResponseSuccess[int](
            data=42,
            is_successful=True,
            err_no=0,
            err_msg="",
        )

        assert resp.is_successful is True
        assert resp.data == 42
        assert resp.err_no == 0
        assert resp.err_msg == ""
        assert resp.meta.operation == "unknown"
        assert resp.meta.started_ns > 0
        assert resp.meta.finished_ns >= resp.meta.started_ns

    def test_type_parameter_works(self):
        """Test generic type parameter works correctly."""
        str_resp = ClientResponseSuccess[str](data="success")
        int_resp = ClientResponseSuccess[int](data=100)

        assert str_resp.data == "success"
        assert int_resp.data == 100
        assert str_resp.meta.venue == Venue.NULL
        assert int_resp.meta.transport == ClientResponseTransport.INTERNAL

    def test_allows_explicit_metadata(self):
        """Test success response can carry explicit metadata."""
        meta = ClientResponseMeta.immediate(
            venue=Venue.BYBIT,
            transport=ClientResponseTransport.WS,
            operation="order.create",
            request_id="123",
            status_code=0,
        )
        resp = ClientResponseSuccess[int](data=1, meta=meta)

        assert resp.meta.venue == Venue.BYBIT
        assert resp.meta.transport == ClientResponseTransport.WS
        assert resp.meta.operation == "order.create"
        assert resp.meta.request_id == "123"

    def test_rejects_non_zero_error_code(self):
        """Test success response rejects non-zero error code."""
        if __debug__:
            with pytest.raises(
                ValueError, match="ClientResponseSuccess err_no must be 0"
            ):
                ClientResponseSuccess[int](data=1, err_no=1)
        else:
            ClientResponseSuccess[int](data=1, err_no=1)

    def test_rejects_non_empty_error_message(self):
        """Test success response rejects non-empty error message."""
        if __debug__:
            with pytest.raises(
                ValueError, match="ClientResponseSuccess err_msg must be empty"
            ):
                ClientResponseSuccess[int](data=1, err_msg="unexpected")
        else:
            ClientResponseSuccess[int](data=1, err_msg="unexpected")


class TestClientResponseFailure:
    """Test ClientResponseFailure."""

    def test_creation_with_error(self):
        """Test creating failure response with error."""
        resp = ClientResponseFailure[Any](
            is_successful=False,
            err_no=1001,
            err_msg="Invalid request",
            data=None,
        )

        assert resp.is_successful is False
        assert resp.err_no == 1001
        assert resp.err_msg == "Invalid request"
        assert resp.data is None
        assert resp.meta.operation == "unknown"
        assert resp.meta.started_ns > 0
        assert resp.meta.finished_ns >= resp.meta.started_ns

    def test_rejects_non_none_data(self):
        """Test failure response rejects non-None payload data."""
        if __debug__:
            with pytest.raises(
                ValueError, match="ClientResponseFailure data must be None"
            ):
                ClientResponseFailure[str](
                    is_successful=False,
                    err_no=500,
                    err_msg="Partial failure",
                    data="partial_data",  # type: ignore[arg-type]
                )
        else:
            ClientResponseFailure[str](
                is_successful=False,
                err_no=500,
                err_msg="Partial failure",
                data="partial_data",  # type: ignore[arg-type]
            )

    def test_rejects_missing_error_details(self):
        """Test failure response requires error code or message."""
        if __debug__:
            with pytest.raises(
                ValueError,
                match="ClientResponseFailure requires err_no or err_msg",
            ):
                ClientResponseFailure[int](is_successful=False)
        else:
            ClientResponseFailure[int](is_successful=False)


class TestIsSuccess:
    """Test the is_success type guard helper."""

    def test_returns_true_for_success_response(self):
        """Test is_success returns True for success variant."""
        response: ClientResponse[int] = ClientResponseSuccess[int](data=123)

        assert is_success(response) is True

    def test_returns_false_for_failure_response(self):
        """Test is_success returns False for failure variant."""
        response: ClientResponse[int] = ClientResponseFailure[int](
            is_successful=False,
            err_no=400,
            err_msg="bad request",
        )

        assert is_success(response) is False


class TestClientResponseMeta:
    """Test ClientResponseMeta behavior."""

    def test_immediate_metadata_defaults(self):
        """Test immediate metadata creation with explicit values."""
        meta = ClientResponseMeta.immediate(
            venue=Venue.OKX,
            transport=ClientResponseTransport.HTTP,
            operation="/api/v5/market/ticker",
            status_code=200,
        )

        assert meta.venue == Venue.OKX
        assert meta.transport == ClientResponseTransport.HTTP
        assert meta.operation == "/api/v5/market/ticker"
        assert meta.status_code == 200
        assert meta.latency_ns == 0
        assert meta.latency_ms == 0.0

    def test_rejects_invalid_timestamps(self):
        """Test metadata rejects finish times earlier than start."""
        if __debug__:
            with pytest.raises(
                ValueError,
                match="ClientResponseMeta.finished_ns must be >= started_ns",
            ):
                ClientResponseMeta(
                    started_ns=2,
                    finished_ns=1,
                    venue=Venue.BYBIT,
                    transport=ClientResponseTransport.HTTP,
                    operation="/v5/market/tickers",
                )
        else:
            ClientResponseMeta(
                started_ns=2,
                finished_ns=1,
                venue=Venue.BYBIT,
                transport=ClientResponseTransport.HTTP,
                operation="/v5/market/tickers",
            )


class TestCreateOrderResponse:
    """Test CreateOrderResponse composite struct."""

    def test_creation_with_all_fields(self, sample_instrument, envelope_kwargs):
        """Test creating CreateOrderResponse."""
        action = CreateOrder(
            instrument=sample_instrument,
            size=1.0,
            is_buy=True,
            price=100.0,
            is_maker=True,
            tif=OrderTimeInForce.PO,
            reduce_only=False,
            client_order_id=ClientOrderId("client123"),
        )
        resp = CreateOrderResponse(
            **{**envelope_kwargs, "origin_id": action.origin_id},
            order_id=OrderId("order123"),
            client_order_id=ClientOrderId("client123"),
        )

        assert resp.origin_id == action.origin_id
        assert resp.order_id == "order123"
        assert resp.client_order_id == "client123"


class TestAmendOrderResponse:
    """Test AmendOrderResponse composite struct."""

    def test_creation_with_all_fields(self, sample_instrument, envelope_kwargs):
        """Test creating AmendOrderResponse."""
        action = AmendOrder(
            instrument=sample_instrument,
            size=2.0,
            price=101.0,
            order_id=OrderId("order123"),
        )
        resp = AmendOrderResponse(
            **{**envelope_kwargs, "origin_id": action.origin_id},
            order_id=OrderId("order123"),
            client_order_id=ClientOrderId("client123"),
        )

        assert resp.origin_id == action.origin_id
        assert resp.order_id == "order123"
        assert resp.client_order_id == "client123"


class TestCancelOrderResponse:
    """Test CancelOrderResponse composite struct."""

    def test_creation_with_all_fields(self, sample_instrument, envelope_kwargs):
        """Test creating CancelOrderResponse."""
        action = CancelOrder(
            instrument=sample_instrument,
            order_id=OrderId("order123"),
        )
        resp = CancelOrderResponse(
            **{**envelope_kwargs, "origin_id": action.origin_id},
            order_id=OrderId("order123"),
            client_order_id=ClientOrderId("client123"),
        )

        assert resp.origin_id == action.origin_id
        assert resp.order_id == "order123"
        assert resp.client_order_id == "client123"


class TestCancelAllOrdersResponse:
    """Test CancelAllOrdersResponse composite struct."""

    def test_creation_with_order_ids(self, sample_instrument, envelope_kwargs):
        """Test creating CancelAllOrdersResponse with order IDs."""
        action = CancelAllOrders(
            instrument=sample_instrument,
            order_ids=[OrderId("order1"), OrderId("order2")],
        )
        resp = CancelAllOrdersResponse(
            **{**envelope_kwargs, "origin_id": action.origin_id},
            order_ids=(OrderId("order1"), OrderId("order2")),
            client_order_ids=(
                ClientOrderId("client1"),
                ClientOrderId("client2"),
            ),
        )

        assert resp.origin_id == action.origin_id
        assert resp.order_ids == ("order1", "order2")
        assert resp.client_order_ids == ("client1", "client2")


class TestTradesResponse:
    """Test TradesResponse composite struct."""

    def test_creation_with_trades(self, envelope_kwargs):
        """Test creating TradesResponse."""
        trades = (
            Trade(time_ms=100, price=100.0, is_buy=True, size=1.0),
            Trade(time_ms=200, price=101.0, is_buy=False, size=2.0),
        )
        resp = TradesResponse(
            **envelope_kwargs,
            trades=trades,
        )

        assert len(resp.trades) == 2

    def test_post_init_rejects_unsorted_trades(self, envelope_kwargs):
        """Test __post_init__ rejects trades out of time order."""
        t1 = Trade(time_ms=200, price=100.0, is_buy=True, size=1.0)
        t2 = Trade(time_ms=100, price=101.0, is_buy=False, size=2.0)

        with pytest.raises(ValueError, match="Invalid trades"):
            TradesResponse(
                **envelope_kwargs,
                trades=(t1, t2),
            )

    def test_zero_size_trade_raises(self, envelope_kwargs):
        """Test zero-size trades are rejected."""
        with pytest.raises(ValueError, match="Invalid size"):
            TradesResponse(
                **envelope_kwargs,
                trades=(Trade(time_ms=100, price=100.0, is_buy=True, size=0.0),),
            )


class TestOrderbookResponse:
    """Test OrderbookResponse composite struct."""

    def test_creation_with_bids_and_asks(self, envelope_kwargs):
        """Test creating OrderbookResponse."""
        bids = (
            OrderbookLevel(price=99.0, size=1.0),
            OrderbookLevel(price=98.0, size=2.0),
        )
        asks = (
            OrderbookLevel(price=101.0, size=1.5),
            OrderbookLevel(price=102.0, size=2.5),
        )

        resp = OrderbookResponse(
            **envelope_kwargs,
            bids=bids,
            asks=asks,
            is_bbo=True,
        )

        assert len(resp.bids) == 2
        assert len(resp.asks) == 2
        assert resp.is_bbo is True

    def test_post_init_rejects_unsorted_levels(self, envelope_kwargs):
        """Test __post_init__ rejects orderbook levels out of price order."""
        b1 = OrderbookLevel(price=100.0, size=1.0)
        b2 = OrderbookLevel(price=99.0, size=2.0)
        a1 = OrderbookLevel(price=102.0, size=1.0)
        a2 = OrderbookLevel(price=101.0, size=2.0)

        with pytest.raises(ValueError, match="Invalid bids"):
            OrderbookResponse(
                **envelope_kwargs,
                bids=(b1, b2),
                asks=(a1, a2),
                is_bbo=False,
            )


class TestOrderbookResponseValidation:
    """Test OrderbookResponse validation behavior."""

    def test_empty_bids_and_asks_raise(self, envelope_kwargs):
        """Test empty orderbook responses raise a ValueError."""
        with pytest.raises(ValueError, match="Invalid OrderbookResponse"):
            OrderbookResponse(
                **envelope_kwargs,
                bids=(),
                asks=(),
                is_bbo=False,
            )


class TestTickerResponse:
    """Test TickerResponse composite struct."""

    def test_creation_with_all_fields(self, envelope_kwargs):
        """Test creating TickerResponse with all fields."""
        resp = TickerResponse(
            **envelope_kwargs,
            mark_price=100.0,
            index_price=99.0,
            funding_rate=0.01,
            next_funding_time_ms=123456789.0,
            open_interest=10000.0,
            avg_volume_24h=5000.0,
            price_chg_24h=5.0,
        )

        assert resp.mark_price == 100.0
        assert resp.index_price == 99.0
        assert resp.funding_rate == 0.01
        assert resp.next_funding_time_ms == 123456789.0
        assert resp.open_interest == 10000.0
        assert resp.avg_volume_24h == 5000.0
        assert resp.price_chg_24h == 5.0


class TestTickerResponseValidation:
    """Test TickerResponse validation behavior."""

    @pytest.mark.parametrize(
        "field,value,match",
        [
            ("mark_price", -1.0, "Invalid mark_price"),
            ("index_price", -1.0, "Invalid index_price"),
            ("next_funding_time_ms", -1.0, "Invalid next_funding_time_ms"),
            ("open_interest", -1.0, "Invalid open_interest"),
            ("avg_volume_24h", -1.0, "Invalid avg_volume_24h"),
        ],
    )
    def test_negative_values_raise(self, envelope_kwargs, field, value, match):
        """Test negative ticker fields raise ValueError."""
        payload = dict(
            **envelope_kwargs,
            mark_price=100.0,
            index_price=99.0,
            funding_rate=0.01,
            next_funding_time_ms=123456789.0,
            open_interest=10000.0,
            avg_volume_24h=5000.0,
            price_chg_24h=5.0,
        )
        payload[field] = value

        with pytest.raises(ValueError, match=match):
            TickerResponse(**payload)


class TestInstrumentInfoResponse:
    """Test InstrumentInfoResponse composite struct."""

    def test_creation_with_all_fields(self, envelope_kwargs):
        """Test creating InstrumentInfoResponse."""
        resp = InstrumentInfoResponse(
            **envelope_kwargs,
            tick_size=0.1,
            lot_size=0.01,
            max_taker_size=100.0,
            max_maker_size=200.0,
        )

        assert resp.tick_size == 0.1
        assert resp.lot_size == 0.01
        assert resp.max_taker_size == 100.0
        assert resp.max_maker_size == 200.0


class TestInstrumentInfoResponseValidation:
    """Test InstrumentInfoResponse validation behavior."""

    @pytest.mark.parametrize(
        "field,value,match",
        [
            ("tick_size", 0.0, "Invalid tick_size"),
            ("tick_size", -1.0, "Invalid tick_size"),
            ("lot_size", 0.0, "Invalid lot_size"),
            ("lot_size", -1.0, "Invalid lot_size"),
            ("max_taker_size", -1.0, "Invalid max_taker_size"),
            ("max_maker_size", -1.0, "Invalid max_maker_size"),
        ],
    )
    def test_invalid_values_raise(self, envelope_kwargs, field, value, match):
        """Test instrument info validation for invalid sizes."""
        payload = dict(
            **envelope_kwargs,
            tick_size=0.1,
            lot_size=0.01,
            max_taker_size=100.0,
            max_maker_size=200.0,
        )
        payload[field] = value

        with pytest.raises(ValueError, match=match):
            InstrumentInfoResponse(**payload)


class TestOrdersResponse:
    """Test OrdersResponse composite struct."""

    def test_creation_with_orders(self, envelope_kwargs):
        """Test creating OrdersResponse."""
        orders = (
            Order(
                create_time_ms=123.0,
                order_id=OrderId("order1"),
                price=100.0,
                is_buy=True,
                size=1.0,
                size_remaining=0.5,
                tif=OrderTimeInForce.GTC,
                is_cancelled=False,
                is_reduce_only=False,
            ),
            Order(
                create_time_ms=124.0,
                order_id=OrderId("order2"),
                price=101.0,
                is_buy=False,
                size=2.0,
                size_remaining=1.0,
                tif=OrderTimeInForce.IOC,
                is_cancelled=False,
                is_reduce_only=True,
            ),
        )

        resp = OrdersResponse(
            **envelope_kwargs,
            orders=orders,
        )

        assert len(resp.orders) == 2
        assert resp.orders[0].order_id == "order1"
        assert resp.orders[1].order_id == "order2"


class TestPositionResponse:
    """Test PositionResponse composite struct."""

    def test_creation_with_all_fields(self, envelope_kwargs):
        """Test creating PositionResponse."""
        resp = PositionResponse(
            **envelope_kwargs,
            price=100.0,
            is_long=True,
            size=1.5,
        )

        assert resp.price == 100.0
        assert resp.is_long is True
        assert resp.size == 1.5
        assert resp.value == 150.0  # price * size


class TestPositionResponseValidation:
    """Test PositionResponse validation behavior."""

    @pytest.mark.parametrize(
        "price,size,match",
        [
            (-1.0, 1.0, "Invalid price"),
            (100.0, -1.0, "Invalid size"),
        ],
    )
    def test_negative_values_raise(self, envelope_kwargs, price, size, match):
        """Test negative position values raise ValueError."""
        with pytest.raises(ValueError, match=match):
            PositionResponse(
                **envelope_kwargs,
                price=price,
                is_long=True,
                size=size,
            )


class TestExecutionResponse:
    """Test ExecutionResponse composite struct."""

    def test_creation_with_executions(self, envelope_kwargs):
        """Test creating ExecutionResponse."""
        executions = (
            Execution(
                exec_time_ms=123.0,
                order_id=OrderId("order1"),
                price=100.0,
                is_buy=True,
                size=1.0,
                is_maker=False,
                fee_paid=0.01,
            ),
            Execution(
                exec_time_ms=124.0,
                order_id=OrderId("order2"),
                price=101.0,
                is_buy=False,
                size=2.0,
                is_maker=True,
                fee_paid=0.02,
            ),
        )

        resp = ExecutionResponse(
            **envelope_kwargs,
            executions=executions,
        )

        assert len(resp.executions) == 2
        assert resp.executions[0].fee_paid == 0.01
        assert resp.executions[1].fee_paid == 0.02


class TestAccountResponse:
    """Test AccountResponse composite struct."""

    def test_creation_with_all_fields(self, envelope_kwargs):
        """Test creating AccountResponse."""
        resp = AccountResponse(
            **envelope_kwargs,
            balance=1000.0,
            initial_margin=100.0,
            maintenance_margin=50.0,
            unrealized_pnl=10.0,
        )

        assert resp.balance == 1000.0
        assert resp.initial_margin == 100.0
        assert resp.maintenance_margin == 50.0
        assert resp.unrealized_pnl == 10.0


class TestAccountResponseValidation:
    """Test AccountResponse validation behavior."""

    @pytest.mark.parametrize(
        "field,value,match",
        [
            ("balance", -1.0, "Invalid balance"),
            ("initial_margin", -1.0, "Invalid initial_margin"),
            ("maintenance_margin", -1.0, "Invalid maintenance_margin"),
        ],
    )
    def test_negative_values_raise(self, envelope_kwargs, field, value, match):
        """Test negative account values raise ValueError."""
        payload = dict(
            **envelope_kwargs,
            balance=1000.0,
            initial_margin=100.0,
            maintenance_margin=50.0,
            unrealized_pnl=10.0,
        )
        payload[field] = value

        with pytest.raises(ValueError, match=match):
            AccountResponse(**payload)


class TestTypeUnions:
    """Test type union aliases work correctly."""

    def test_order_action_response_types(self, sample_instrument, envelope_kwargs):
        """Test AnyOrderActionResponse types."""
        action = CreateOrder(
            instrument=sample_instrument,
            size=1.0,
            is_buy=True,
            price=100.0,
            is_maker=True,
            tif=OrderTimeInForce.PO,
            reduce_only=False,
        )
        create_resp = CreateOrderResponse(
            **{**envelope_kwargs, "origin_id": action.origin_id},
            order_id=OrderId("order123"),
        )

        # Type should be valid
        assert isinstance(create_resp, CreateOrderResponse)

    def test_client_response_types(self, envelope_kwargs):
        """Test AnyClientResponse types."""
        trades_resp = TradesResponse(
            **envelope_kwargs,
            trades=(Trade(time_ms=100, price=100.0, is_buy=True, size=1.0),),
        )

        # Type should be valid
        assert isinstance(trades_resp, TradesResponse)

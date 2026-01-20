"""Tests for framework.base.trading.models module.

Tests cover:
- Order action structs (CreateOrder, AmendOrder, CancelOrder, CancelAllOrders)
- Secret struct for credential management
- Client response types (Success/Failure)
- Trading response structs (all *Response classes)
- Type unions (AnyOrderActionResponse, AnyClientResponse)

Tests are organized by dependency layer:
1. Primitives: CreateOrder, AmendOrder, CancelOrder, CancelAllOrders, Secret, ClientResponse
2. Composites: All *Response classes with CoreSchema
"""

from __future__ import annotations

from typing import Any

import pytest

from framework.base.common import Instrument, InstrumentType, Venue
from framework.base.stream.models import (
    Execution,
    Moments,
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
    ClientResponseFailure,
    ClientResponseSuccess,
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
)


# =============================================================================
# HELPER FIXTURES
# =============================================================================


@pytest.fixture
def sample_instrument():
    """Reusable instrument for tests."""
    return Instrument(
        venue=Venue.BINANCE_USDM,
        base="BTC",
        quote="USDT",
        symbol="BTCUSDT",
        code=1,
        instrument_type=InstrumentType.PERPETUAL,
    )


@pytest.fixture
def sample_moments():
    """Reusable Moments for CoreSchema."""
    return Moments(exch_time_ns=1000, recv_time_ns=2000)


# =============================================================================
# LAYER 1: PRIMITIVES
# =============================================================================


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
            client_order_id="client123",
        )

        assert order.size == 1.0
        assert order.is_buy is True
        assert order.price == 100.0
        assert order.is_maker is True
        assert order.tif == OrderTimeInForce.PO
        assert order.reduce_only is False
        assert order.client_order_id == "client123"

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
            order_id="order123",
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
            client_order_id="client123",
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
                order_id="order123",
            )

    def test_price_must_be_positive_when_provided(self, sample_instrument):
        """Test price must be > 0 when provided."""
        with pytest.raises(ValueError, match="Price must be greater than 0"):
            AmendOrder(
                instrument=sample_instrument,
                size=1.0,
                price=0.0,
                order_id="order123",
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
        if should_raise:
            with pytest.raises(ValueError):
                AmendOrder(
                    instrument=sample_instrument,
                    size=size,
                    price=price,
                    order_id=order_id,
                    client_order_id=client_order_id,
                )
        else:
            order = AmendOrder(
                instrument=sample_instrument,
                size=size,
                price=price,
                order_id=order_id,
                client_order_id=client_order_id,
            )
            assert order.size == size


class TestCancelOrder:
    """Test CancelOrder validation."""

    def test_creation_with_order_id(self, sample_instrument):
        """Test creating CancelOrder with order_id."""
        order = CancelOrder(
            instrument=sample_instrument,
            order_id="order123",
            client_order_id=None,
        )

        assert order.order_id == "order123"
        assert order.client_order_id is None

    def test_creation_with_client_order_id(self, sample_instrument):
        """Test creating CancelOrder with client_order_id."""
        order = CancelOrder(
            instrument=sample_instrument,
            order_id=None,
            client_order_id="client123",
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
            order_ids=["order1", "order2"],
            client_order_ids=None,
        )

        assert order.order_ids == ["order1", "order2"]
        assert order.client_order_ids is None

    def test_creation_with_client_order_ids(self, sample_instrument):
        """Test creating CancelAllOrders with client_order_ids list."""
        order = CancelAllOrders(
            instrument=sample_instrument,
            order_ids=None,
            client_order_ids=["client1", "client2"],
        )

        assert order.order_ids is None
        assert order.client_order_ids == ["client1", "client2"]

    def test_creation_with_both_id_lists(self, sample_instrument):
        """Test creating CancelAllOrders with both ID lists."""
        order = CancelAllOrders(
            instrument=sample_instrument,
            order_ids=["order1"],
            client_order_ids=["client1"],
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

    def test_load_missing_variable_raises(self):
        """Test load() raises for missing environment variable."""
        with pytest.raises(RuntimeError, match="Failed to load.*from '.env'"):
            Secret.load("NONEXISTENT_VARIABLE_XYZ")


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

    def test_type_parameter_works(self):
        """Test generic type parameter works correctly."""
        str_resp = ClientResponseSuccess[str](data="success")
        int_resp = ClientResponseSuccess[int](data=100)

        assert str_resp.data == "success"
        assert int_resp.data == 100


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

    def test_can_include_partial_data(self):
        """Test failure response can include partial data."""
        resp = ClientResponseFailure[str](
            is_successful=False,
            err_no=500,
            err_msg="Partial failure",
            data="partial_data",
        )

        assert resp.is_successful is False
        assert resp.data == "partial_data"


# =============================================================================
# LAYER 2: COMPOSITES (Response Structs)
# =============================================================================


class TestCreateOrderResponse:
    """Test CreateOrderResponse composite struct."""

    def test_creation_with_all_fields(self, sample_instrument, sample_moments):
        """Test creating CreateOrderResponse."""
        trigger = CreateOrder(
            instrument=sample_instrument,
            size=1.0,
            is_buy=True,
            price=100.0,
            is_maker=True,
            tif=OrderTimeInForce.PO,
            reduce_only=False,
            client_order_id="client123",
        )
        resp = CreateOrderResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            trigger=trigger,
            order_id="order123",
            client_order_id="client123",
        )

        assert resp.trigger == trigger
        assert resp.order_id == "order123"
        assert resp.client_order_id == "client123"


class TestAmendOrderResponse:
    """Test AmendOrderResponse composite struct."""

    def test_creation_with_all_fields(self, sample_instrument, sample_moments):
        """Test creating AmendOrderResponse."""
        trigger = AmendOrder(
            instrument=sample_instrument,
            size=2.0,
            price=101.0,
            order_id="order123",
        )
        resp = AmendOrderResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            trigger=trigger,
            order_id="order123",
            client_order_id="client123",
        )

        assert resp.trigger == trigger
        assert resp.order_id == "order123"
        assert resp.client_order_id == "client123"


class TestCancelOrderResponse:
    """Test CancelOrderResponse composite struct."""

    def test_creation_with_all_fields(self, sample_instrument, sample_moments):
        """Test creating CancelOrderResponse."""
        trigger = CancelOrder(
            instrument=sample_instrument,
            order_id="order123",
        )
        resp = CancelOrderResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            trigger=trigger,
            order_id="order123",
            client_order_id="client123",
        )

        assert resp.trigger == trigger
        assert resp.order_id == "order123"
        assert resp.client_order_id == "client123"


class TestCancelAllOrdersResponse:
    """Test CancelAllOrdersResponse composite struct."""

    def test_creation_with_order_ids(self, sample_instrument, sample_moments):
        """Test creating CancelAllOrdersResponse with order IDs."""
        trigger = CancelAllOrders(
            instrument=sample_instrument,
            order_ids=["order1", "order2"],
        )
        resp = CancelAllOrdersResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            trigger=trigger,
            order_ids=["order1", "order2"],
            client_order_ids=["client1", "client2"],
        )

        assert resp.trigger == trigger
        assert resp.order_ids == ["order1", "order2"]
        assert resp.client_order_ids == ["client1", "client2"]


class TestTradesResponse:
    """Test TradesResponse composite struct."""

    def test_creation_with_trades(self, sample_instrument, sample_moments):
        """Test creating TradesResponse."""
        trades = [
            Trade(time_ms=100, price=100.0, is_buy=True, size=1.0),
            Trade(time_ms=200, price=101.0, is_buy=False, size=2.0),
        ]
        resp = TradesResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            trades=trades,
        )

        assert len(resp.trades) == 2

    def test_post_init_sorting_by_time(self, sample_instrument, sample_moments):
        """Test __post_init__ sorts trades by time_ms."""
        t1 = Trade(time_ms=200, price=100.0, is_buy=True, size=1.0)
        t2 = Trade(time_ms=100, price=101.0, is_buy=False, size=2.0)

        resp = TradesResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            trades=[t1, t2],
        )

        assert resp.trades[0].time_ms == 100
        assert resp.trades[1].time_ms == 200


class TestOrderbookResponse:
    """Test OrderbookResponse composite struct."""

    def test_creation_with_bids_and_asks(self, sample_instrument, sample_moments):
        """Test creating OrderbookResponse."""
        bids = [
            OrderbookLevel(price=99.0, size=1.0),
            OrderbookLevel(price=98.0, size=2.0),
        ]
        asks = [
            OrderbookLevel(price=101.0, size=1.5),
            OrderbookLevel(price=102.0, size=2.5),
        ]

        resp = OrderbookResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            bids=bids,
            asks=asks,
            is_bbo=True,
            is_snapshot=True,
        )

        assert len(resp.bids) == 2
        assert len(resp.asks) == 2
        assert resp.is_bbo is True
        assert resp.is_snapshot is True

    def test_post_init_sorting(self, sample_instrument, sample_moments):
        """Test __post_init__ sorts bids and asks by price."""
        b1 = OrderbookLevel(price=100.0, size=1.0)
        b2 = OrderbookLevel(price=99.0, size=2.0)
        a1 = OrderbookLevel(price=102.0, size=1.0)
        a2 = OrderbookLevel(price=101.0, size=2.0)

        resp = OrderbookResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            bids=[b1, b2],
            asks=[a1, a2],
            is_bbo=False,
            is_snapshot=True,
        )

        assert resp.bids[0].price == 99.0
        assert resp.bids[1].price == 100.0
        assert resp.asks[0].price == 101.0
        assert resp.asks[1].price == 102.0


class TestTickerResponse:
    """Test TickerResponse composite struct."""

    def test_creation_with_all_fields(self, sample_instrument, sample_moments):
        """Test creating TickerResponse with all fields."""
        resp = TickerResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
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


class TestInstrumentInfoResponse:
    """Test InstrumentInfoResponse composite struct."""

    def test_creation_with_all_fields(self, sample_instrument, sample_moments):
        """Test creating InstrumentInfoResponse."""
        resp = InstrumentInfoResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            tick_size=0.1,
            lot_size=0.01,
            max_taker_size=100.0,
            max_maker_size=200.0,
        )

        assert resp.tick_size == 0.1
        assert resp.lot_size == 0.01
        assert resp.max_taker_size == 100.0
        assert resp.max_maker_size == 200.0


class TestOrdersResponse:
    """Test OrdersResponse composite struct."""

    def test_creation_with_orders(self, sample_instrument, sample_moments):
        """Test creating OrdersResponse."""
        orders = [
            Order(
                create_time_ms=123.0,
                order_id="order1",
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
                order_id="order2",
                price=101.0,
                is_buy=False,
                size=2.0,
                size_remaining=1.0,
                tif=OrderTimeInForce.IOC,
                is_cancelled=False,
                is_reduce_only=True,
            ),
        ]

        resp = OrdersResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            orders=orders,
        )

        assert len(resp.orders) == 2
        assert resp.orders[0].order_id == "order1"
        assert resp.orders[1].order_id == "order2"


class TestPositionResponse:
    """Test PositionResponse composite struct."""

    def test_creation_with_all_fields(self, sample_instrument, sample_moments):
        """Test creating PositionResponse."""
        resp = PositionResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            price=100.0,
            is_long=True,
            size=1.5,
        )

        assert resp.price == 100.0
        assert resp.is_long is True
        assert resp.size == 1.5
        assert resp.value == 150.0  # price * size


class TestExecutionResponse:
    """Test ExecutionResponse composite struct."""

    def test_creation_with_executions(self, sample_instrument, sample_moments):
        """Test creating ExecutionResponse."""
        executions = [
            Execution(
                exec_time_ms=123.0,
                order_id="order1",
                price=100.0,
                is_buy=True,
                size=1.0,
                is_maker=False,
                fee_paid=0.01,
            ),
            Execution(
                exec_time_ms=124.0,
                order_id="order2",
                price=101.0,
                is_buy=False,
                size=2.0,
                is_maker=True,
                fee_paid=0.02,
            ),
        ]

        resp = ExecutionResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            executions=executions,
        )

        assert len(resp.executions) == 2
        assert resp.executions[0].fee_paid == 0.01
        assert resp.executions[1].fee_paid == 0.02


class TestAccountResponse:
    """Test AccountResponse composite struct."""

    def test_creation_with_all_fields(self, sample_instrument, sample_moments):
        """Test creating AccountResponse."""
        resp = AccountResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            balance=1000.0,
            initial_margin=100.0,
            maintenance_margin=50.0,
            unrealized_pnl=10.0,
        )

        assert resp.balance == 1000.0
        assert resp.initial_margin == 100.0
        assert resp.maintenance_margin == 50.0
        assert resp.unrealized_pnl == 10.0


class TestTypeUnions:
    """Test type union aliases work correctly."""

    def test_order_action_response_types(self, sample_instrument, sample_moments):
        """Test AnyOrderActionResponse types."""
        create_resp = CreateOrderResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            trigger=CreateOrder(
                instrument=sample_instrument,
                size=1.0,
                is_buy=True,
                price=100.0,
                is_maker=True,
                tif=OrderTimeInForce.PO,
                reduce_only=False,
            ),
            order_id="order123",
        )

        # Type should be valid
        assert isinstance(create_resp, CreateOrderResponse)

    def test_client_response_types(self, sample_instrument, sample_moments):
        """Test AnyClientResponse types."""
        trades_resp = TradesResponse(
            moments=sample_moments,
            venue=Venue.BINANCE_USDM,
            instrument=sample_instrument,
            trades=[Trade(time_ms=100, price=100.0, is_buy=True, size=1.0)],
        )

        # Type should be valid
        assert isinstance(trades_resp, TradesResponse)

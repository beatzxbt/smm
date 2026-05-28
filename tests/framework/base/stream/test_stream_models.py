"""Tests for framework.base.stream.models module.

Tests cover:
- Stream type enums (MarketDataStreamType, PrivateDataStreamType)
- Trade and OrderbookLevel primitive structs
- Order and Execution primitive structs
- OrderTimeInForce enum
- StreamSchema base class
- Message structs (TradeMsg, OrderbookMsg, TickerMsg, etc.)
- Type unions (MarketDataMsg, PrivateDataMsg, DataMsg)

Tests are organized by dependency layer:
1. Primitives: Trade, OrderbookLevel, Order, Execution, OrderTimeInForce, StreamType enums
2. Composites: StreamSchema, TradeMsg, OrderbookMsg, TickerMsg, PositionMsg, OrderMsg, ExecutionMsg, AccountMsg, DataStreamEventMsg
"""

from __future__ import annotations

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
    AccountMsg,
    Balance,
    DataMsg,
    DataStreamEvent,
    DataStreamEventMsg,
    Execution,
    ExecutionMsg,
    MarketDataStreamType,
    Order,
    OrderbookLevel,
    OrderbookMsg,
    OrderMsg,
    OrderTimeInForce,
    PositionMsg,
    StreamSchema,
    TickerMsg,
    Trade,
    TradeMsg,
    Msg,
)


@pytest.fixture
def sample_instrument():
    """Reusable instrument for stream schema tests."""
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
def core_kwargs(sample_instrument):
    """Reusable StreamSchema kwargs."""
    moments = Moments()
    message_id = MessageId(recv_time_ns=moments.recv_time_ns)
    return {
        "id": message_id,
        "origin_id": message_id,
        "moments": moments,
        "instrument": sample_instrument,
        "is_snapshot": False,
    }


class TestTrade:
    """Test Trade struct."""

    def test_creation_with_valid_data(self):
        """Test creating Trade with valid data."""
        trade = Trade(time_ms=1234567890, price=100.0, is_buy=True, size=1.5)

        assert trade.time_ms == 1234567890
        assert trade.price == 100.0
        assert trade.is_buy is True
        assert trade.size == 1.5

    def test_notional_size_property(self):
        """Test notional_size returns price * size."""
        trade = Trade(time_ms=123, price=100.0, is_buy=True, size=2.0)
        assert trade.notional_size == 200.0

    def test_as_tuple(self):
        """Test as_tuple returns trade fields in wire order."""
        trade = Trade(time_ms=123, price=100.0, is_buy=True, size=2.0)
        assert trade.as_tuple() == (123, 100.0, True, 2.0)

    def test_buy_and_sell_flags(self):
        """Test is_buy flag for both buy and sell trades."""
        buy_trade = Trade(time_ms=123, price=100.0, is_buy=True, size=1.0)
        sell_trade = Trade(time_ms=124, price=100.0, is_buy=False, size=1.0)

        assert buy_trade.is_buy is True
        assert sell_trade.is_buy is False

    def test_small_positive_size(self):
        """Test trade with very small positive size."""
        trade = Trade(time_ms=123, price=100.0, is_buy=True, size=1e-12)
        assert trade.size == 1e-12
        assert trade.notional_size == 1e-10

    def test_large_values(self):
        """Test trade with large price and size values."""
        trade = Trade(time_ms=123, price=50000.0, is_buy=True, size=100.0)
        assert trade.notional_size == 5000000.0


class TestTradeValidation:
    """Test Trade validation errors."""

    def test_invalid_time_raises(self):
        """Test time_ms must be > 0."""
        with pytest.raises(ValueError, match="Invalid time_ms"):
            Trade(time_ms=0, price=100.0, is_buy=True, size=1.0)

    def test_invalid_price_raises(self):
        """Test price must be > 0."""
        with pytest.raises(ValueError, match="Invalid price"):
            Trade(time_ms=1, price=0.0, is_buy=True, size=1.0)

    def test_zero_size_raises(self):
        """Test size must be > 0."""
        with pytest.raises(ValueError, match="Invalid size"):
            Trade(time_ms=1, price=1.0, is_buy=True, size=0.0)

    def test_invalid_size_raises(self):
        """Test negative size raises ValueError."""
        with pytest.raises(ValueError, match="Invalid size"):
            Trade(time_ms=1, price=1.0, is_buy=True, size=-1.0)


class TestOrderbookLevel:
    """Test OrderbookLevel struct."""

    def test_creation_with_required_fields(self):
        """Test creating OrderbookLevel with required fields."""
        level = OrderbookLevel(price=100.0, size=5.0)

        assert level.price == 100.0
        assert level.size == 5.0
        assert level.num_orders == 1  # Default value

    def test_creation_with_num_orders(self):
        """Test creating OrderbookLevel with num_orders."""
        level = OrderbookLevel(price=100.0, size=5.0, num_orders=10)
        assert level.num_orders == 10

    def test_notional_size_property(self):
        """Test notional_size returns price * size."""
        level = OrderbookLevel(price=100.0, size=5.0)
        assert level.notional_size == 500.0

    def test_as_tuple(self):
        """Test as_tuple returns level fields in wire order."""
        level = OrderbookLevel(price=100.0, size=5.0, num_orders=2)
        assert level.as_tuple() == (100.0, 5.0, 2)

    def test_zero_size(self):
        """Test orderbook level with zero size."""
        level = OrderbookLevel(price=100.0, size=0.0)
        assert level.size == 0.0
        assert level.notional_size == 0.0

    def test_multiple_orders(self):
        """Test orderbook level with multiple orders."""
        level = OrderbookLevel(price=100.0, size=10.0, num_orders=5)
        assert level.num_orders == 5


class TestOrderbookLevelValidation:
    """Test OrderbookLevel validation errors."""

    def test_invalid_price_raises(self):
        """Test price must be > 0."""
        with pytest.raises(ValueError, match="Invalid price"):
            OrderbookLevel(price=0.0, size=1.0)

    def test_invalid_size_raises(self):
        """Test size must be >= 0."""
        with pytest.raises(ValueError, match="Invalid size"):
            OrderbookLevel(price=1.0, size=-1.0)

    def test_invalid_num_orders_raises(self):
        """Test num_orders must be >= 0."""
        with pytest.raises(ValueError, match="Invalid num_orders"):
            OrderbookLevel(price=1.0, size=1.0, num_orders=-1)


class TestOrderTimeInForce:
    """Test OrderTimeInForce enum."""

    def test_enum_values_exist(self):
        """Test all expected TIF values exist."""
        assert OrderTimeInForce.GTC == "GoodTillCanceled"
        assert OrderTimeInForce.IOC == "ImmediateOrCancel"
        assert OrderTimeInForce.PO == "PostOnly"
        assert OrderTimeInForce.FOK == "FillOrKill"


class TestOrder:
    """Test Order struct."""

    def test_creation_with_all_fields(self):
        """Test creating Order with all fields."""
        order = Order(
            create_time_ms=123.0,
            order_id=OrderId("order123"),
            price=100.0,
            is_buy=True,
            size=1.5,
            size_remaining=0.5,
            tif=OrderTimeInForce.GTC,
            is_cancelled=False,
            is_reduce_only=True,
            client_order_id=ClientOrderId("client123"),
        )

        assert order.create_time_ms == 123.0
        assert order.order_id == "order123"
        assert order.price == 100.0
        assert order.is_buy is True
        assert order.size == 1.5
        assert order.size_remaining == 0.5
        assert order.tif == OrderTimeInForce.GTC
        assert order.is_cancelled is False
        assert order.is_reduce_only is True
        assert order.client_order_id == "client123"

    def test_notional_size_property(self):
        """Test notional_size returns price * size."""
        order = Order(
            create_time_ms=123.0,
            order_id=OrderId("order123"),
            price=100.0,
            is_buy=True,
            size=2.0,
            size_remaining=1.0,
            tif=OrderTimeInForce.GTC,
            is_cancelled=False,
            is_reduce_only=False,
        )
        assert order.notional_size == 200.0

    def test_optional_client_order_id_none(self):
        """Test Order with None client_order_id."""
        order = Order(
            create_time_ms=123.0,
            order_id=OrderId("order123"),
            price=100.0,
            is_buy=True,
            size=1.0,
            size_remaining=1.0,
            tif=OrderTimeInForce.GTC,
            is_cancelled=False,
            is_reduce_only=False,
            client_order_id=None,
        )
        assert order.client_order_id is None

    def test_cancelled_order(self):
        """Test cancelled order."""
        order = Order(
            create_time_ms=123.0,
            order_id=OrderId("order123"),
            price=100.0,
            is_buy=True,
            size=1.0,
            size_remaining=0.0,
            tif=OrderTimeInForce.GTC,
            is_cancelled=True,
            is_reduce_only=False,
        )
        assert order.is_cancelled is True
        assert order.size_remaining == 0.0

    def test_different_tif_values(self):
        """Test orders with different TIF values."""
        for tif in [
            OrderTimeInForce.GTC,
            OrderTimeInForce.IOC,
            OrderTimeInForce.PO,
            OrderTimeInForce.FOK,
        ]:
            order = Order(
                create_time_ms=123.0,
                order_id=OrderId("order123"),
                price=100.0,
                is_buy=True,
                size=1.0,
                size_remaining=1.0,
                tif=tif,
                is_cancelled=False,
                is_reduce_only=False,
            )
            assert order.tif == tif


class TestOrderValidation:
    """Test Order validation errors."""

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            (
                {
                    "create_time_ms": 0.0,
                    "order_id": "order123",
                    "price": 100.0,
                    "size": 1.0,
                    "size_remaining": 1.0,
                },
                "Invalid create_time_ms",
            ),
            (
                {
                    "create_time_ms": 1.0,
                    "order_id": "",
                    "price": 100.0,
                    "size": 1.0,
                    "size_remaining": 1.0,
                },
                "Invalid order_id",
            ),
            (
                {
                    "create_time_ms": 1.0,
                    "order_id": "order123",
                    "price": 0.0,
                    "size": 1.0,
                    "size_remaining": 1.0,
                },
                "Invalid price",
            ),
            (
                {
                    "create_time_ms": 1.0,
                    "order_id": "order123",
                    "price": 100.0,
                    "size": -1.0,
                    "size_remaining": 0.0,
                },
                "Invalid size",
            ),
            (
                {
                    "create_time_ms": 1.0,
                    "order_id": "order123",
                    "price": 100.0,
                    "size": 1.0,
                    "size_remaining": -1.0,
                },
                "Invalid size_remaining",
            ),
            (
                {
                    "create_time_ms": 1.0,
                    "order_id": "order123",
                    "price": 100.0,
                    "size": 1.0,
                    "size_remaining": 2.0,
                },
                "Invalid size_remaining",
            ),
        ],
    )
    def test_invalid_order_fields_raise(
        self, kwargs: dict[str, float | str], message: str
    ):
        """Test order field validation errors."""
        with pytest.raises(ValueError, match=message):
            Order(
                is_buy=True,
                tif=OrderTimeInForce.GTC,
                is_cancelled=False,
                is_reduce_only=False,
                **kwargs,
            )


class TestExecution:
    """Test Execution struct."""

    def test_creation_with_all_fields(self):
        """Test creating Execution with all fields."""
        execution = Execution(
            exec_time_ms=123.0,
            order_id=OrderId("order123"),
            price=100.0,
            is_buy=True,
            size=1.5,
            is_maker=False,
            fee_paid=0.015,
            client_order_id=ClientOrderId("client123"),
        )

        assert execution.exec_time_ms == 123.0
        assert execution.order_id == "order123"
        assert execution.price == 100.0
        assert execution.is_buy is True
        assert execution.size == 1.5
        assert execution.is_maker is False
        assert execution.fee_paid == 0.015
        assert execution.client_order_id == "client123"

    def test_notional_size_property(self):
        """Test notional_size returns price * size."""
        execution = Execution(
            exec_time_ms=123.0,
            order_id=OrderId("order123"),
            price=100.0,
            is_buy=True,
            size=2.0,
            is_maker=True,
        )
        assert execution.notional_size == 200.0

    def test_maker_and_taker_flags(self):
        """Test is_maker flag for both maker and taker executions."""
        maker_exec = Execution(
            exec_time_ms=123.0,
            order_id=OrderId("order123"),
            price=100.0,
            is_buy=True,
            size=1.0,
            is_maker=True,
        )
        taker_exec = Execution(
            exec_time_ms=124.0,
            order_id=OrderId("order124"),
            price=100.0,
            is_buy=False,
            size=1.0,
            is_maker=False,
        )

        assert maker_exec.is_maker is True
        assert taker_exec.is_maker is False

    def test_default_fee_paid(self):
        """Test default fee_paid value."""
        execution = Execution(
            exec_time_ms=123.0,
            order_id=OrderId("order123"),
            price=100.0,
            is_buy=True,
            size=1.0,
            is_maker=True,
        )
        assert execution.fee_paid == 0.0

    def test_optional_client_order_id_none(self):
        """Test Execution with None client_order_id."""
        execution = Execution(
            exec_time_ms=123.0,
            order_id=OrderId("order123"),
            price=100.0,
            is_buy=True,
            size=1.0,
            is_maker=True,
            client_order_id=None,
        )
        assert execution.client_order_id is None


class TestExecutionValidation:
    """Test Execution validation errors."""

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            (
                {
                    "exec_time_ms": 0.0,
                    "order_id": "order123",
                    "price": 100.0,
                    "size": 1.0,
                },
                "Invalid exec_time_ms",
            ),
            (
                {
                    "exec_time_ms": 1.0,
                    "order_id": "",
                    "price": 100.0,
                    "size": 1.0,
                },
                "Invalid order_id",
            ),
            (
                {
                    "exec_time_ms": 1.0,
                    "order_id": "order123",
                    "price": 0.0,
                    "size": 1.0,
                },
                "Invalid price",
            ),
            (
                {
                    "exec_time_ms": 1.0,
                    "order_id": "order123",
                    "price": 100.0,
                    "size": -1.0,
                },
                "Invalid size",
            ),
        ],
    )
    def test_invalid_execution_fields_raise(
        self, kwargs: dict[str, float | str], message: str
    ):
        """Test execution field validation errors."""
        with pytest.raises(ValueError, match=message):
            Execution(
                is_buy=True,
                is_maker=False,
                **kwargs,
            )


class TestStreamSchema:
    """Test StreamSchema base class."""

    def test_creation_with_valid_data(self, core_kwargs):
        """Test creating StreamSchema with valid data."""
        schema = StreamSchema(**core_kwargs)

        assert isinstance(schema.moments, Moments)
        assert schema.venue == Venue.BINANCE_USDM
        assert isinstance(schema.instrument, Instrument)
        assert schema.id == schema.origin_id
        assert schema.id.recv_time_ns == schema.moments.recv_time_ns
        assert schema.is_snapshot is False

    def test_moments_field(self, sample_instrument):
        """Test StreamSchema with specific Moments."""
        moments = Moments(exch_time_ns=1000, recv_time_ns=2000)
        message_id = MessageId(recv_time_ns=moments.recv_time_ns)
        schema = StreamSchema(
            id=message_id,
            origin_id=message_id,
            moments=moments,
            instrument=sample_instrument,
            is_snapshot=False,
        )

        assert schema.moments.exch_time_ns == 1000
        assert schema.moments.recv_time_ns == 2000
        assert schema.id.recv_time_ns == 2000
        assert schema.origin_id.recv_time_ns == 2000
        assert schema.is_snapshot is False

    def test_recv_time_mismatch_raises(self, sample_instrument):
        """Test StreamSchema rejects id timestamps that do not match moments."""
        if not __debug__:
            pytest.skip("Debug-only invariant checks are disabled under -O")

        moments = Moments(exch_time_ns=1000, recv_time_ns=2000)
        message_id = MessageId(recv_time_ns=3000)

        with pytest.raises(
            ValueError, match="id.recv_time_ns; expected to match moments.recv_time_ns"
        ):
            StreamSchema(
                id=message_id,
                origin_id=message_id,
                moments=moments,
                instrument=sample_instrument,
                is_snapshot=False,
            )


class TestTradeMsg:
    """Test TradeMsg composite struct."""

    def test_creation_with_trades(self, core_kwargs):
        """Test creating TradeMsg with trades."""
        t1 = Trade(time_ms=100, price=100.0, is_buy=True, size=1.0)
        t2 = Trade(time_ms=200, price=101.0, is_buy=False, size=2.0)

        msg = TradeMsg(trades=(t1, t2), **core_kwargs)

        assert len(msg.trades) == 2
        assert isinstance(msg.trades, tuple)
        assert msg.trades[0] == t1
        assert msg.trades[1] == t2

    def test_post_init_rejects_decreasing_time(self, core_kwargs):
        """Test __post_init__ rejects trades that move backward in time."""
        t1 = Trade(time_ms=200, price=100.0, is_buy=True, size=1.0)
        t2 = Trade(time_ms=100, price=101.0, is_buy=False, size=2.0)
        t3 = Trade(time_ms=150, price=102.0, is_buy=True, size=1.5)

        with pytest.raises(ValueError, match="increasing order"):
            TradeMsg(trades=(t1, t2, t3), **core_kwargs)

    def test_equal_trade_times_are_allowed(self, core_kwargs):
        """Test __post_init__ allows equal trade timestamps."""
        t1 = Trade(time_ms=100, price=100.0, is_buy=True, size=1.0)
        t2 = Trade(time_ms=100, price=101.0, is_buy=False, size=2.0)

        msg = TradeMsg(trades=(t1, t2), **core_kwargs)

        assert msg.trades[0].time_ms == 100
        assert msg.trades[1].time_ms == 100

    def test_empty_trades_tuple_raises(self, core_kwargs):
        """Test empty trades tuple raises ValueError.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid trades"):
            TradeMsg(trades=(), **core_kwargs)

    def test_single_trade(self, core_kwargs):
        """Test TradeMsg with single trade."""
        t = Trade(time_ms=100, price=100.0, is_buy=True, size=1.0)
        msg = TradeMsg(trades=(t,), **core_kwargs)
        assert len(msg.trades) == 1


class TestOrderbookMsg:
    """Test OrderbookMsg composite struct."""

    def test_creation_with_bids_and_asks(self, core_kwargs):
        """Test creating OrderbookMsg with bids and asks."""
        b1 = OrderbookLevel(price=98.0, size=2.0)
        b2 = OrderbookLevel(price=99.0, size=1.0)
        a1 = OrderbookLevel(price=101.0, size=1.5)
        a2 = OrderbookLevel(price=102.0, size=2.5)

        msg = OrderbookMsg(
            bids=(b1, b2),
            asks=(a1, a2),
            is_bbo=False,
            **{**core_kwargs, "is_snapshot": True},
        )

        assert len(msg.bids) == 2
        assert len(msg.asks) == 2
        assert isinstance(msg.bids, tuple)
        assert isinstance(msg.asks, tuple)

    def test_post_init_rejects_non_increasing_bids(self, core_kwargs):
        """Test __post_init__ rejects bids that are not strictly increasing."""
        b1 = OrderbookLevel(price=100.0, size=1.0)
        b2 = OrderbookLevel(price=99.0, size=2.0)
        b3 = OrderbookLevel(price=101.0, size=1.5)

        with pytest.raises(ValueError, match="strictly increasing prices"):
            OrderbookMsg(
                bids=(b1, b2, b3),
                asks=(),
                is_bbo=False,
                **{**core_kwargs, "is_snapshot": True},
            )

    def test_post_init_rejects_non_increasing_asks(self, core_kwargs):
        """Test __post_init__ rejects asks that are not strictly increasing."""
        a1 = OrderbookLevel(price=102.0, size=1.0)
        a2 = OrderbookLevel(price=101.0, size=2.0)
        a3 = OrderbookLevel(price=103.0, size=1.5)

        with pytest.raises(ValueError, match="strictly increasing prices"):
            OrderbookMsg(
                bids=(),
                asks=(a1, a2, a3),
                is_bbo=False,
                **{**core_kwargs, "is_snapshot": True},
            )

    def test_bbo_flag(self, core_kwargs):
        """Test is_bbo flag."""
        bbo_msg = OrderbookMsg(
            bids=(OrderbookLevel(price=99.0, size=1.0),),
            asks=(OrderbookLevel(price=101.0, size=1.0),),
            is_bbo=True,
            **{**core_kwargs, "is_snapshot": False},
        )

        assert bbo_msg.is_bbo is True

    def test_snapshot_flag(self, core_kwargs):
        """Test is_snapshot flag.

        Args:
            core_kwargs: Core schema fixture values.
        """
        snapshot_msg = OrderbookMsg(
            bids=(OrderbookLevel(price=99.0, size=1.0),),
            asks=(OrderbookLevel(price=101.0, size=1.0),),
            is_bbo=False,
            **{**core_kwargs, "is_snapshot": True},
        )

        assert snapshot_msg.is_snapshot is True

    def test_empty_orderbook_is_allowed(self, core_kwargs):
        """Test empty orderbook payloads are allowed.

        Args:
            core_kwargs: Core schema fixture values.
        """
        msg = OrderbookMsg(
            bids=(),
            asks=(),
            is_bbo=False,
            **{**core_kwargs, "is_snapshot": True},
        )

        assert msg.bids == ()
        assert msg.asks == ()


class TestTickerMsg:
    """Test TickerMsg composite struct."""

    def test_creation_with_all_fields(self, core_kwargs):
        """Test creating TickerMsg with all fields."""
        msg = TickerMsg(
            mark_price=100.0,
            index_price=99.5,
            funding_rate=0.01,
            funding_period_min=480,
            next_funding_time_ms=123456789.0,
            open_interest=10000.0,
            avg_volume_24h=5000.0,
            price_chg_24h_pct=0.05,
            **core_kwargs,
        )

        assert msg.mark_price == 100.0
        assert msg.index_price == 99.5
        assert msg.funding_rate == 0.01
        assert msg.funding_period_min == 480
        assert msg.next_funding_time_ms == 123456789.0
        assert msg.open_interest == 10000.0
        assert msg.avg_volume_24h == 5000.0
        assert msg.price_chg_24h_pct == 0.05

    def test_negative_funding_rate(self, core_kwargs):
        """Test TickerMsg with negative funding rate."""
        msg = TickerMsg(
            mark_price=100.0,
            index_price=99.5,
            funding_rate=-0.01,
            funding_period_min=480,
            next_funding_time_ms=123456789.0,
            open_interest=10000.0,
            avg_volume_24h=5000.0,
            price_chg_24h_pct=-0.05,
            **core_kwargs,
        )

        assert msg.funding_rate == -0.01
        assert msg.price_chg_24h_pct == -0.05


class TestTickerMsgValidation:
    """Test TickerMsg validation errors."""

    def test_negative_mark_price_raises(self, core_kwargs):
        """Test mark_price must be >= 0.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid mark_price"):
            TickerMsg(
                mark_price=-1.0,
                index_price=1.0,
                funding_rate=0.0,
                funding_period_min=480,
                next_funding_time_ms=0.0,
                open_interest=0.0,
                avg_volume_24h=0.0,
                price_chg_24h_pct=0.0,
                **core_kwargs,
            )

    def test_negative_index_price_raises(self, core_kwargs):
        """Test index_price must be >= 0.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid index_price"):
            TickerMsg(
                mark_price=1.0,
                index_price=-1.0,
                funding_rate=0.0,
                funding_period_min=480,
                next_funding_time_ms=0.0,
                open_interest=0.0,
                avg_volume_24h=0.0,
                price_chg_24h_pct=0.0,
                **core_kwargs,
            )

    def test_negative_next_funding_time_raises(self, core_kwargs):
        """Test next_funding_time_ms must be >= 0.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid next_funding_time_ms"):
            TickerMsg(
                mark_price=1.0,
                index_price=1.0,
                funding_rate=0.0,
                funding_period_min=480,
                next_funding_time_ms=-1.0,
                open_interest=0.0,
                avg_volume_24h=0.0,
                price_chg_24h_pct=0.0,
                **core_kwargs,
            )

    def test_negative_open_interest_raises(self, core_kwargs):
        """Test open_interest must be >= 0.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid open_interest"):
            TickerMsg(
                mark_price=1.0,
                index_price=1.0,
                funding_rate=0.0,
                funding_period_min=480,
                next_funding_time_ms=0.0,
                open_interest=-1.0,
                avg_volume_24h=0.0,
                price_chg_24h_pct=0.0,
                **core_kwargs,
            )

    def test_negative_volume_raises(self, core_kwargs):
        """Test avg_volume_24h must be >= 0.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid avg_volume_24h"):
            TickerMsg(
                mark_price=1.0,
                index_price=1.0,
                funding_rate=0.0,
                funding_period_min=480,
                next_funding_time_ms=0.0,
                open_interest=0.0,
                avg_volume_24h=-1.0,
                price_chg_24h_pct=0.0,
                **core_kwargs,
            )

    def test_price_change_below_limit_raises(self, core_kwargs):
        """Test price_chg_24h_pct must be >= -100.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid price_chg_24h_pct"):
            TickerMsg(
                mark_price=1.0,
                index_price=1.0,
                funding_rate=0.0,
                funding_period_min=480,
                next_funding_time_ms=0.0,
                open_interest=0.0,
                avg_volume_24h=0.0,
                price_chg_24h_pct=-101.0,
                **core_kwargs,
            )

    def test_invalid_funding_period_raises(self, core_kwargs):
        """Test funding_period_min must be > 0."""
        with pytest.raises(ValueError, match="Invalid funding_period_min"):
            TickerMsg(
                mark_price=1.0,
                index_price=1.0,
                funding_rate=0.0,
                funding_period_min=0,
                next_funding_time_ms=0.0,
                open_interest=0.0,
                avg_volume_24h=0.0,
                price_chg_24h_pct=0.0,
                **core_kwargs,
            )


class TestPositionMsg:
    """Test PositionMsg composite struct."""

    def test_creation_with_all_fields(self, core_kwargs):
        """Test creating PositionMsg with all fields."""
        msg = PositionMsg(
            price=100.0,
            is_long=True,
            size=1.5,
            **core_kwargs,
        )

        assert msg.price == 100.0
        assert msg.is_long is True
        assert msg.size == 1.5

    def test_notional_size_property(self, core_kwargs):
        """Test notional_size returns price * size."""
        msg = PositionMsg(
            price=100.0,
            is_long=True,
            size=2.0,
            **core_kwargs,
        )
        assert msg.notional_size == 200.0

    def test_long_and_short_positions(self, core_kwargs):
        """Test is_long flag for both long and short positions."""
        long_msg = PositionMsg(price=100.0, is_long=True, size=1.0, **core_kwargs)
        short_msg = PositionMsg(price=100.0, is_long=False, size=1.0, **core_kwargs)

        assert long_msg.is_long is True
        assert short_msg.is_long is False


class TestOrderMsg:
    """Test OrderMsg composite struct."""

    def test_creation_with_orders(self, core_kwargs):
        """Test creating OrderMsg with orders."""
        order1 = Order(
            create_time_ms=123.0,
            order_id=OrderId("order1"),
            price=100.0,
            is_buy=True,
            size=1.0,
            size_remaining=0.5,
            tif=OrderTimeInForce.GTC,
            is_cancelled=False,
            is_reduce_only=False,
        )
        order2 = Order(
            create_time_ms=124.0,
            order_id=OrderId("order2"),
            price=101.0,
            is_buy=False,
            size=2.0,
            size_remaining=1.0,
            tif=OrderTimeInForce.IOC,
            is_cancelled=False,
            is_reduce_only=True,
        )

        msg = OrderMsg(orders=(order1, order2), **core_kwargs)

        assert len(msg.orders) == 2
        assert isinstance(msg.orders, tuple)
        assert msg.orders[0].order_id == "order1"
        assert msg.orders[1].order_id == "order2"

    def test_empty_orders_tuple_raises(self, core_kwargs):
        """Test empty orders tuple raises ValueError.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid orders"):
            OrderMsg(orders=(), **core_kwargs)


class TestExecutionMsg:
    """Test ExecutionMsg composite struct."""

    def test_creation_with_executions(self, core_kwargs):
        """Test creating ExecutionMsg with executions."""
        exec1 = Execution(
            exec_time_ms=123.0,
            order_id=OrderId("order1"),
            price=100.0,
            is_buy=True,
            size=1.0,
            is_maker=False,
            fee_paid=0.01,
        )
        exec2 = Execution(
            exec_time_ms=124.0,
            order_id=OrderId("order2"),
            price=101.0,
            is_buy=False,
            size=2.0,
            is_maker=True,
            fee_paid=0.02,
        )

        msg = ExecutionMsg(executions=(exec1, exec2), **core_kwargs)

        assert len(msg.executions) == 2
        assert isinstance(msg.executions, tuple)
        assert msg.executions[0].fee_paid == 0.01
        assert msg.executions[1].fee_paid == 0.02

    def test_decreasing_execution_times_raise(self, core_kwargs):
        """Test executions must be ordered oldest to newest."""
        exec1 = Execution(
            exec_time_ms=124.0,
            order_id=OrderId("order1"),
            price=100.0,
            is_buy=True,
            size=1.0,
            is_maker=False,
        )
        exec2 = Execution(
            exec_time_ms=123.0,
            order_id=OrderId("order2"),
            price=101.0,
            is_buy=False,
            size=2.0,
            is_maker=True,
        )

        with pytest.raises(ValueError, match="increasing order"):
            ExecutionMsg(executions=(exec1, exec2), **core_kwargs)

    def test_empty_executions_tuple_raises(self, core_kwargs):
        """Test empty executions tuple raises ValueError.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid executions"):
            ExecutionMsg(executions=(), **core_kwargs)


class TestAccountMsg:
    """Test AccountMsg composite struct."""

    def test_creation_with_all_fields(self, core_kwargs):
        """Test creating AccountMsg with all fields."""
        msg = AccountMsg(
            balances={
                core_kwargs["instrument"]: Balance(currency="USDT", amount=1000.0)
            },
            initial_margin=100.0,
            maintenance_margin=50.0,
            unrealized_pnl=10.0,
            **core_kwargs,
        )

        assert msg.balances[core_kwargs["instrument"]].amount == 1000.0
        assert msg.initial_margin == 100.0
        assert msg.maintenance_margin == 50.0
        assert msg.unrealized_pnl == 10.0

    def test_negative_pnl(self, core_kwargs):
        """Test AccountMsg with negative unrealized PnL."""
        msg = AccountMsg(
            balances={
                core_kwargs["instrument"]: Balance(currency="USDT", amount=1000.0)
            },
            initial_margin=100.0,
            maintenance_margin=50.0,
            unrealized_pnl=-25.0,
            **core_kwargs,
        )

        assert msg.unrealized_pnl == -25.0


class TestDataStreamEvent:
    """Test DataStreamEvent enum and simple payload preservation."""

    def test_event_values(self):
        """Test DataStreamEvent exposes expected string values."""
        assert DataStreamEvent.START.value == "START"
        assert DataStreamEvent.STOP.value == "STOP"
        assert DataStreamEvent.SUBSCRIBE.value == "SUBSCRIBE"
        assert DataStreamEvent.UNSUBSCRIBE.value == "UNSUBSCRIBE"
        assert DataStreamEvent.HEARTBEAT.value == "HEARTBEAT"

    def test_event_msg_fields(self, core_kwargs):
        """Test DataStreamEventMsg preserves explicit input fields."""
        instrument = core_kwargs["instrument"]
        msg = DataStreamEventMsg(
            venue=Venue.BINANCE_USDM,
            event=DataStreamEvent.SUBSCRIBE,
            changes={MarketDataStreamType.TICKER: instrument},
            state={MarketDataStreamType.TICKER: instrument},
            time_ms=123456,
        )

        assert msg.venue == Venue.BINANCE_USDM
        assert msg.event == DataStreamEvent.SUBSCRIBE
        assert msg.changes == {MarketDataStreamType.TICKER: instrument}
        assert msg.state == {MarketDataStreamType.TICKER: instrument}
        assert msg.time_ms == 123456


class TestHeartbeatEvent:
    """Test heartbeat DataStreamEventMsg payloads."""

    def test_creation_with_all_fields(self, core_kwargs):
        """Test creating heartbeat event with all fields."""
        instrument = core_kwargs["instrument"]
        msg = DataStreamEventMsg(
            time_ms=123456,
            venue=Venue.BINANCE_USDM,
            event=DataStreamEvent.HEARTBEAT,
            changes={},
            state={MarketDataStreamType.TICKER: instrument},
            time_next_check_ms=123556,
        )

        assert msg.venue == Venue.BINANCE_USDM
        assert msg.event == DataStreamEvent.HEARTBEAT
        assert msg.time_ms == 123456
        assert msg.time_next_check_ms == 123556

    def test_time_next_greater_than_time_now(self, core_kwargs):
        """Test that time_next_check_ms > time_ms."""
        instrument = core_kwargs["instrument"]
        msg = DataStreamEventMsg(
            time_ms=100,
            venue=Venue.BINANCE_USDM,
            event=DataStreamEvent.HEARTBEAT,
            changes={},
            state={MarketDataStreamType.TICKER: instrument},
            time_next_check_ms=200,
        )

        assert msg.time_next_check_ms is not None
        assert msg.time_next_check_ms > msg.time_ms

    def test_different_venues(self, core_kwargs):
        """Test heartbeat events with different venues."""
        instrument = core_kwargs["instrument"]
        for venue in [Venue.BINANCE_USDM, Venue.BYBIT, Venue.OKX]:
            msg = DataStreamEventMsg(
                time_ms=100,
                venue=venue,
                event=DataStreamEvent.HEARTBEAT,
                changes={},
                state={MarketDataStreamType.TICKER: instrument},
                time_next_check_ms=200,
            )
            assert msg.venue == venue


class TestLifecycleEvents:
    """Test non-heartbeat DataStreamEventMsg payloads."""

    def test_start_event_with_state(self, core_kwargs):
        """Test START event preserves state and defaults.

        Args:
            core_kwargs (dict[str, object]): Core schema fixture values.
        """
        instrument = core_kwargs["instrument"]
        state = {MarketDataStreamType.TICKER: instrument}

        msg = DataStreamEventMsg(
            time_ms=100,
            venue=Venue.BINANCE_USDM,
            event=DataStreamEvent.START,
            changes={},
            state=state,
        )

        assert msg.event == DataStreamEvent.START
        assert msg.changes == {}
        assert msg.state == state
        assert msg.time_next_check_ms is None

    def test_stop_event_with_empty_state(self):
        """Test STOP event accepts empty state."""
        msg = DataStreamEventMsg(
            time_ms=200,
            venue=Venue.BINANCE_USDM,
            event=DataStreamEvent.STOP,
            changes={},
            state={},
        )

        assert msg.event == DataStreamEvent.STOP
        assert msg.state == {}
        assert msg.time_next_check_ms is None

    def test_subscribe_event_tracks_changes(self, core_kwargs):
        """Test SUBSCRIBE event tracks changes and state.

        Args:
            core_kwargs (dict[str, object]): Core schema fixture values.
        """
        instrument = core_kwargs["instrument"]
        changes = {MarketDataStreamType.TRADES: instrument}
        state = {
            MarketDataStreamType.TICKER: instrument,
            MarketDataStreamType.TRADES: instrument,
        }

        msg = DataStreamEventMsg(
            time_ms=300,
            venue=Venue.BINANCE_USDM,
            event=DataStreamEvent.SUBSCRIBE,
            changes=changes,
            state=state,
        )

        assert msg.event == DataStreamEvent.SUBSCRIBE
        assert msg.changes == changes
        assert msg.state == state

    def test_unsubscribe_event_tracks_changes(self, core_kwargs):
        """Test UNSUBSCRIBE event tracks changes and state.

        Args:
            core_kwargs (dict[str, object]): Core schema fixture values.
        """
        instrument = core_kwargs["instrument"]
        changes = {MarketDataStreamType.TICKER: instrument}
        state = {}

        msg = DataStreamEventMsg(
            time_ms=400,
            venue=Venue.BINANCE_USDM,
            event=DataStreamEvent.UNSUBSCRIBE,
            changes=changes,
            state=state,
        )

        assert msg.event == DataStreamEvent.UNSUBSCRIBE
        assert msg.changes == changes
        assert msg.state == state


class TestTypeUnions:
    """Test type union aliases work correctly."""

    def test_market_data_msg_types_assignable(self, core_kwargs):
        """Test MarketDataMsg types are assignable.

        Args:
            core_kwargs: Core schema fixture values.
        """

        def accept_market_msg(msg: DataMsg) -> None:
            pass

        trade = Trade(time_ms=100, price=100.0, is_buy=True, size=1.0)
        trade_msg = TradeMsg(trades=(trade,), **core_kwargs)
        orderbook_msg = OrderbookMsg(
            bids=(OrderbookLevel(price=99.0, size=1.0),),
            asks=(OrderbookLevel(price=101.0, size=1.0),),
            is_bbo=True,
            **{**core_kwargs, "is_snapshot": True},
        )
        ticker_msg = TickerMsg(
            mark_price=0.0,
            index_price=0.0,
            funding_rate=0.0,
            funding_period_min=480,
            next_funding_time_ms=0.0,
            open_interest=0.0,
            avg_volume_24h=0.0,
            price_chg_24h_pct=0.0,
            **core_kwargs,
        )

        # Should not raise type errors
        accept_market_msg(trade_msg)
        accept_market_msg(orderbook_msg)
        accept_market_msg(ticker_msg)

    def test_private_data_msg_types_assignable(self, core_kwargs):
        """Test PrivateDataMsg types are assignable.

        Args:
            core_kwargs: Core schema fixture values.
        """

        def accept_private_msg(msg: DataMsg) -> None:
            pass

        position_msg = PositionMsg(price=100.0, is_long=True, size=1.0, **core_kwargs)
        order = Order(
            create_time_ms=123.0,
            order_id=OrderId("order1"),
            price=100.0,
            is_buy=True,
            size=1.0,
            size_remaining=0.0,
            tif=OrderTimeInForce.GTC,
            is_cancelled=False,
            is_reduce_only=False,
        )
        execution = Execution(
            exec_time_ms=123.0,
            order_id=OrderId("order1"),
            price=100.0,
            is_buy=True,
            size=1.0,
            is_maker=True,
        )
        order_msg = OrderMsg(orders=(order,), **core_kwargs)
        execution_msg = ExecutionMsg(executions=(execution,), **core_kwargs)
        account_msg = AccountMsg(
            balances={
                core_kwargs["instrument"]: Balance(currency="USDT", amount=1000.0)
            },
            initial_margin=100.0,
            maintenance_margin=50.0,
            unrealized_pnl=0.0,
            **core_kwargs,
        )

        # Should not raise type errors
        accept_private_msg(position_msg)
        accept_private_msg(order_msg)
        accept_private_msg(execution_msg)
        accept_private_msg(account_msg)

    def test_event_msgs_assignable(self, core_kwargs):
        """Test DataStreamEventMsg variants are assignable to Msg.

        Args:
            core_kwargs (dict[str, object]): Core schema fixture values.
        """

        def accept_msg(msg: Msg) -> None:
            pass

        instrument = core_kwargs["instrument"]
        event_msgs = [
            DataStreamEventMsg(
                time_ms=100,
                venue=Venue.BINANCE_USDM,
                event=DataStreamEvent.HEARTBEAT,
                changes={},
                state={MarketDataStreamType.TICKER: instrument},
                time_next_check_ms=200,
            ),
            DataStreamEventMsg(
                time_ms=110,
                venue=Venue.BINANCE_USDM,
                event=DataStreamEvent.START,
                changes={},
                state={MarketDataStreamType.TICKER: instrument},
            ),
            DataStreamEventMsg(
                time_ms=120,
                venue=Venue.BINANCE_USDM,
                event=DataStreamEvent.STOP,
                changes={},
                state={},
            ),
            DataStreamEventMsg(
                time_ms=130,
                venue=Venue.BINANCE_USDM,
                event=DataStreamEvent.SUBSCRIBE,
                changes={MarketDataStreamType.TRADES: instrument},
                state={
                    MarketDataStreamType.TICKER: instrument,
                    MarketDataStreamType.TRADES: instrument,
                },
            ),
            DataStreamEventMsg(
                time_ms=140,
                venue=Venue.BINANCE_USDM,
                event=DataStreamEvent.UNSUBSCRIBE,
                changes={MarketDataStreamType.TICKER: instrument},
                state={},
            ),
        ]

        # Should not raise type error
        for msg in event_msgs:
            accept_msg(msg)

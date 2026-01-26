"""Tests for framework.base.stream.models module.

Tests cover:
- Stream type enums (MarketDataStreamType, PrivateDataStreamType)
- Moments timing struct
- Trade and OrderbookLevel primitive structs
- Order and Execution primitive structs
- OrderTimeInForce enum
- CoreSchema base class
- Message structs (TradeMsg, OrderbookMsg, TickerMsg, etc.)
- Type unions (MarketDataMsg, PrivateDataMsg, DataMsg)

Tests are organized by dependency layer:
1. Primitives: Moments, Trade, OrderbookLevel, Order, Execution, OrderTimeInForce, StreamType enums
2. Composites: CoreSchema, TradeMsg, OrderbookMsg, TickerMsg, PositionMsg, OrderMsg, ExecutionMsg, AccountMsg, DataStreamEventMsg
"""

from __future__ import annotations

import pytest

from framework.base.common import Instrument, InstrumentType, Venue
from framework.base.stream.models import (
    AccountMsg,
    CoreSchema,
    DataMsg,
    DataStreamEvent,
    DataStreamEventMsg,
    Execution,
    ExecutionMsg,
    MarketDataStreamType,
    Moments,
    Order,
    OrderbookLevel,
    OrderbookMsg,
    OrderMsg,
    OrderTimeInForce,
    PositionMsg,
    TickerMsg,
    Trade,
    TradeMsg,
    Msg,
)


@pytest.fixture
def sample_instrument():
    """Reusable instrument for CoreSchema tests."""
    return Instrument(
        venue=Venue.BINANCE_USDM,
        base="BTC",
        quote="USDT",
        symbol="BTCUSDT",
        code=1,
        instrument_type=InstrumentType.PERPETUAL,
    )


@pytest.fixture
def core_kwargs(sample_instrument):
    """Reusable CoreSchema kwargs."""
    return {
        "moments": Moments(),
        "venue": Venue.BINANCE_USDM,
        "instrument": sample_instrument,
    }


class TestMoments:
    """Test Moments timing struct."""

    def test_creation_with_defaults(self):
        """Test creating Moments with default time values."""
        m = Moments()
        assert m.exch_time_ns > 0
        assert m.recv_time_ns > 0

    def test_creation_with_explicit_times(self):
        """Test creating Moments with explicit time values."""
        m = Moments(exch_time_ns=1000, recv_time_ns=2000)
        assert m.exch_time_ns == 1000
        assert m.recv_time_ns == 2000

    def test_elapsed_since_exch_ns_is_nonnegative(self):
        """Test elapsed time since exchange is non-negative."""
        m = Moments()
        elapsed = m.elapsed_since_exch_ns()
        assert elapsed >= 0

    def test_elapsed_since_recv_ns_is_nonnegative(self):
        """Test elapsed time since receive is non-negative."""
        m = Moments()
        elapsed = m.elapsed_since_recv_ns()
        assert elapsed >= 0

    def test_elapsed_methods_increase_over_time(self):
        """Test that elapsed time methods return increasing values."""
        m = Moments(exch_time_ns=100, recv_time_ns=100)

        # Elapsed should be positive and growing
        first_elapsed = m.elapsed_since_exch_ns()
        assert first_elapsed > 0


class TestTrade:
    """Test Trade struct."""

    def test_creation_with_valid_data(self):
        """Test creating Trade with valid data."""
        trade = Trade(time_ms=1234567890, price=100.0, is_buy=True, size=1.5)

        assert trade.time_ms == 1234567890
        assert trade.price == 100.0
        assert trade.is_buy is True
        assert trade.size == 1.5

    def test_value_property(self):
        """Test value property returns price * size."""
        trade = Trade(time_ms=123, price=100.0, is_buy=True, size=2.0)
        assert trade.value == 200.0

    def test_buy_and_sell_flags(self):
        """Test is_buy flag for both buy and sell trades."""
        buy_trade = Trade(time_ms=123, price=100.0, is_buy=True, size=1.0)
        sell_trade = Trade(time_ms=124, price=100.0, is_buy=False, size=1.0)

        assert buy_trade.is_buy is True
        assert sell_trade.is_buy is False

    def test_zero_size(self):
        """Test trade with zero size."""
        trade = Trade(time_ms=123, price=100.0, is_buy=True, size=0.0)
        assert trade.size == 0.0
        assert trade.value == 0.0

    def test_large_values(self):
        """Test trade with large price and size values."""
        trade = Trade(time_ms=123, price=50000.0, is_buy=True, size=100.0)
        assert trade.value == 5000000.0


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

    def test_invalid_size_raises(self):
        """Test size must be >= 0."""
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

    def test_value_property(self):
        """Test value property returns price * size."""
        level = OrderbookLevel(price=100.0, size=5.0)
        assert level.value == 500.0

    def test_zero_size(self):
        """Test orderbook level with zero size."""
        level = OrderbookLevel(price=100.0, size=0.0)
        assert level.size == 0.0
        assert level.value == 0.0

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

    def test_str_representation(self):
        """Test TIF string representation."""
        assert str(OrderTimeInForce.GTC) == "GoodTillCanceled"
        assert str(OrderTimeInForce.PO) == "PostOnly"

    def test_enum_membership(self):
        """Test enum membership checks."""
        assert OrderTimeInForce.GTC in OrderTimeInForce
        assert OrderTimeInForce.FOK in OrderTimeInForce


class TestOrder:
    """Test Order struct."""

    def test_creation_with_all_fields(self):
        """Test creating Order with all fields."""
        order = Order(
            create_time_ms=123.0,
            order_id="order123",
            price=100.0,
            is_buy=True,
            size=1.5,
            size_remaining=0.5,
            tif=OrderTimeInForce.GTC,
            is_cancelled=False,
            is_reduce_only=True,
            client_order_id="client123",
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

    def test_value_property(self):
        """Test value property returns price * size."""
        order = Order(
            create_time_ms=123.0,
            order_id="order123",
            price=100.0,
            is_buy=True,
            size=2.0,
            size_remaining=1.0,
            tif=OrderTimeInForce.GTC,
            is_cancelled=False,
            is_reduce_only=False,
        )
        assert order.value == 200.0

    def test_optional_client_order_id_none(self):
        """Test Order with None client_order_id."""
        order = Order(
            create_time_ms=123.0,
            order_id="order123",
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
            order_id="order123",
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
                order_id="order123",
                price=100.0,
                is_buy=True,
                size=1.0,
                size_remaining=1.0,
                tif=tif,
                is_cancelled=False,
                is_reduce_only=False,
            )
            assert order.tif == tif


class TestExecution:
    """Test Execution struct."""

    def test_creation_with_all_fields(self):
        """Test creating Execution with all fields."""
        execution = Execution(
            exec_time_ms=123.0,
            order_id="order123",
            price=100.0,
            is_buy=True,
            size=1.5,
            is_maker=False,
            fee_paid=0.015,
            client_order_id="client123",
        )

        assert execution.exec_time_ms == 123.0
        assert execution.order_id == "order123"
        assert execution.price == 100.0
        assert execution.is_buy is True
        assert execution.size == 1.5
        assert execution.is_maker is False
        assert execution.fee_paid == 0.015
        assert execution.client_order_id == "client123"

    def test_value_property(self):
        """Test value property returns price * size."""
        execution = Execution(
            exec_time_ms=123.0,
            order_id="order123",
            price=100.0,
            is_buy=True,
            size=2.0,
            is_maker=True,
        )
        assert execution.value == 200.0

    def test_maker_and_taker_flags(self):
        """Test is_maker flag for both maker and taker executions."""
        maker_exec = Execution(
            exec_time_ms=123.0,
            order_id="order123",
            price=100.0,
            is_buy=True,
            size=1.0,
            is_maker=True,
        )
        taker_exec = Execution(
            exec_time_ms=124.0,
            order_id="order124",
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
            order_id="order123",
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
            order_id="order123",
            price=100.0,
            is_buy=True,
            size=1.0,
            is_maker=True,
            client_order_id=None,
        )
        assert execution.client_order_id is None


class TestCoreSchema:
    """Test CoreSchema base class."""

    def test_creation_with_valid_data(self, core_kwargs):
        """Test creating CoreSchema with valid data."""
        schema = CoreSchema(**core_kwargs)

        assert isinstance(schema.moments, Moments)
        assert schema.venue == Venue.BINANCE_USDM
        assert isinstance(schema.instrument, Instrument)

    def test_moments_field(self, sample_instrument):
        """Test CoreSchema with specific Moments."""
        moments = Moments(exch_time_ns=1000, recv_time_ns=2000)
        schema = CoreSchema(
            moments=moments,
            venue=Venue.BYBIT,
            instrument=sample_instrument,
        )

        assert schema.moments.exch_time_ns == 1000
        assert schema.moments.recv_time_ns == 2000

    def test_different_venues(self, sample_instrument):
        """Test CoreSchema with different venues."""
        for venue in [Venue.BINANCE_USDM, Venue.BYBIT, Venue.OKX]:
            schema = CoreSchema(
                moments=Moments(),
                venue=venue,
                instrument=sample_instrument,
            )
            assert schema.venue == venue


class TestTradeMsg:
    """Test TradeMsg composite struct."""

    def test_creation_with_trades(self, core_kwargs):
        """Test creating TradeMsg with trades."""
        t1 = Trade(time_ms=100, price=100.0, is_buy=True, size=1.0)
        t2 = Trade(time_ms=200, price=101.0, is_buy=False, size=2.0)

        msg = TradeMsg(trades=[t1, t2], **core_kwargs)

        assert len(msg.trades) == 2
        assert msg.trades[0] == t1
        assert msg.trades[1] == t2

    def test_post_init_sorting_by_time(self, core_kwargs):
        """Test __post_init__ sorts trades by time_ms."""
        t1 = Trade(time_ms=200, price=100.0, is_buy=True, size=1.0)
        t2 = Trade(time_ms=100, price=101.0, is_buy=False, size=2.0)
        t3 = Trade(time_ms=150, price=102.0, is_buy=True, size=1.5)

        msg = TradeMsg(trades=[t1, t2, t3], **core_kwargs)

        assert msg.trades[0].time_ms == 100
        assert msg.trades[1].time_ms == 150
        assert msg.trades[2].time_ms == 200

    def test_empty_trades_list_raises(self, core_kwargs):
        """Test empty trades list raises ValueError.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid trades"):
            TradeMsg(trades=[], **core_kwargs)

    def test_single_trade(self, core_kwargs):
        """Test TradeMsg with single trade."""
        t = Trade(time_ms=100, price=100.0, is_buy=True, size=1.0)
        msg = TradeMsg(trades=[t], **core_kwargs)
        assert len(msg.trades) == 1


class TestOrderbookMsg:
    """Test OrderbookMsg composite struct."""

    def test_creation_with_bids_and_asks(self, core_kwargs):
        """Test creating OrderbookMsg with bids and asks."""
        b1 = OrderbookLevel(price=99.0, size=1.0)
        b2 = OrderbookLevel(price=98.0, size=2.0)
        a1 = OrderbookLevel(price=101.0, size=1.5)
        a2 = OrderbookLevel(price=102.0, size=2.5)

        msg = OrderbookMsg(
            bids=[b1, b2],
            asks=[a1, a2],
            is_bbo=False,
            is_snapshot=True,
            **core_kwargs,
        )

        assert len(msg.bids) == 2
        assert len(msg.asks) == 2

    def test_post_init_sorting_bids_by_price(self, core_kwargs):
        """Test __post_init__ sorts bids by price (ascending)."""
        b1 = OrderbookLevel(price=100.0, size=1.0)
        b2 = OrderbookLevel(price=99.0, size=2.0)
        b3 = OrderbookLevel(price=101.0, size=1.5)

        msg = OrderbookMsg(
            bids=[b1, b2, b3],
            asks=[],
            is_bbo=False,
            is_snapshot=True,
            **core_kwargs,
        )

        assert msg.bids[0].price == 99.0
        assert msg.bids[1].price == 100.0
        assert msg.bids[2].price == 101.0

    def test_post_init_sorting_asks_by_price(self, core_kwargs):
        """Test __post_init__ sorts asks by price (ascending)."""
        a1 = OrderbookLevel(price=102.0, size=1.0)
        a2 = OrderbookLevel(price=101.0, size=2.0)
        a3 = OrderbookLevel(price=103.0, size=1.5)

        msg = OrderbookMsg(
            bids=[],
            asks=[a1, a2, a3],
            is_bbo=False,
            is_snapshot=True,
            **core_kwargs,
        )

        assert msg.asks[0].price == 101.0
        assert msg.asks[1].price == 102.0
        assert msg.asks[2].price == 103.0

    def test_bbo_flag(self, core_kwargs):
        """Test is_bbo flag."""
        bbo_msg = OrderbookMsg(
            bids=[OrderbookLevel(price=99.0, size=1.0)],
            asks=[OrderbookLevel(price=101.0, size=1.0)],
            is_bbo=True,
            is_snapshot=False,
            **core_kwargs,
        )

        assert bbo_msg.is_bbo is True

    def test_snapshot_flag(self, core_kwargs):
        """Test is_snapshot flag.

        Args:
            core_kwargs: Core schema fixture values.
        """
        snapshot_msg = OrderbookMsg(
            bids=[OrderbookLevel(price=99.0, size=1.0)],
            asks=[OrderbookLevel(price=101.0, size=1.0)],
            is_bbo=False,
            is_snapshot=True,
            **core_kwargs,
        )

        assert snapshot_msg.is_snapshot is True

    def test_empty_orderbook_raises(self, core_kwargs):
        """Test empty orderbook raises ValueError.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid orderbook"):
            OrderbookMsg(
                bids=[],
                asks=[],
                is_bbo=False,
                is_snapshot=True,
                **core_kwargs,
            )


class TestTickerMsg:
    """Test TickerMsg composite struct."""

    def test_creation_with_all_fields(self, core_kwargs):
        """Test creating TickerMsg with all fields."""
        msg = TickerMsg(
            mark_price=100.0,
            index_price=99.5,
            funding_rate=0.01,
            next_funding_time_ms=123456789.0,
            open_interest=10000.0,
            avg_volume_24h=5000.0,
            price_chg_24h_pct=0.05,
            **core_kwargs,
        )

        assert msg.mark_price == 100.0
        assert msg.index_price == 99.5
        assert msg.funding_rate == 0.01
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
                next_funding_time_ms=0.0,
                open_interest=0.0,
                avg_volume_24h=0.0,
                price_chg_24h_pct=-101.0,
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

    def test_value_property(self, core_kwargs):
        """Test value property returns price * size."""
        msg = PositionMsg(
            price=100.0,
            is_long=True,
            size=2.0,
            **core_kwargs,
        )
        assert msg.value == 200.0

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
            order_id="order1",
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
            order_id="order2",
            price=101.0,
            is_buy=False,
            size=2.0,
            size_remaining=1.0,
            tif=OrderTimeInForce.IOC,
            is_cancelled=False,
            is_reduce_only=True,
        )

        msg = OrderMsg(orders=[order1, order2], **core_kwargs)

        assert len(msg.orders) == 2
        assert msg.orders[0].order_id == "order1"
        assert msg.orders[1].order_id == "order2"

    def test_empty_orders_list_raises(self, core_kwargs):
        """Test empty orders list raises ValueError.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid orders"):
            OrderMsg(orders=[], **core_kwargs)


class TestExecutionMsg:
    """Test ExecutionMsg composite struct."""

    def test_creation_with_executions(self, core_kwargs):
        """Test creating ExecutionMsg with executions."""
        exec1 = Execution(
            exec_time_ms=123.0,
            order_id="order1",
            price=100.0,
            is_buy=True,
            size=1.0,
            is_maker=False,
            fee_paid=0.01,
        )
        exec2 = Execution(
            exec_time_ms=124.0,
            order_id="order2",
            price=101.0,
            is_buy=False,
            size=2.0,
            is_maker=True,
            fee_paid=0.02,
        )

        msg = ExecutionMsg(executions=[exec1, exec2], **core_kwargs)

        assert len(msg.executions) == 2
        assert msg.executions[0].fee_paid == 0.01
        assert msg.executions[1].fee_paid == 0.02

    def test_empty_executions_list_raises(self, core_kwargs):
        """Test empty executions list raises ValueError.

        Args:
            core_kwargs: Core schema fixture values.
        """
        with pytest.raises(ValueError, match="Invalid executions"):
            ExecutionMsg(executions=[], **core_kwargs)


class TestAccountMsg:
    """Test AccountMsg composite struct."""

    def test_creation_with_all_fields(self, core_kwargs):
        """Test creating AccountMsg with all fields."""
        msg = AccountMsg(
            balance=1000.0,
            initial_margin=100.0,
            maintenance_margin=50.0,
            unrealized_pnl=10.0,
            **core_kwargs,
        )

        assert msg.balance == 1000.0
        assert msg.initial_margin == 100.0
        assert msg.maintenance_margin == 50.0
        assert msg.unrealized_pnl == 10.0

    def test_negative_pnl(self, core_kwargs):
        """Test AccountMsg with negative unrealized PnL."""
        msg = AccountMsg(
            balance=1000.0,
            initial_margin=100.0,
            maintenance_margin=50.0,
            unrealized_pnl=-25.0,
            **core_kwargs,
        )

        assert msg.unrealized_pnl == -25.0


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
        trade_msg = TradeMsg(trades=[trade], **core_kwargs)
        orderbook_msg = OrderbookMsg(
            bids=[OrderbookLevel(price=99.0, size=1.0)],
            asks=[OrderbookLevel(price=101.0, size=1.0)],
            is_bbo=True,
            is_snapshot=True,
            **core_kwargs,
        )
        ticker_msg = TickerMsg(
            mark_price=0.0,
            index_price=0.0,
            funding_rate=0.0,
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
            order_id="order1",
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
            order_id="order1",
            price=100.0,
            is_buy=True,
            size=1.0,
            is_maker=True,
        )
        order_msg = OrderMsg(orders=[order], **core_kwargs)
        execution_msg = ExecutionMsg(executions=[execution], **core_kwargs)
        account_msg = AccountMsg(
            balance=1000.0,
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

"""Tests for framework.binance.stream.structs conversions."""

from __future__ import annotations

from framework.base.common import (
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Venue,
)
from framework.binance.stream.structs import (
    AccountUpdateStreamUpdate,
    BookTickerStreamUpdate,
    DiffBookDepthStreamUpdate,
    ExecutionReportStreamUpdate,
    MarkPriceStreamUpdate,
    OrderUpdateStreamUpdate,
    PositionUpdateStreamUpdate,
    TradeStreamUpdate,
    OpenInterestInfo,
    TickerStats24h,
)


def make_collection() -> InstrumentCollection:
    """Create an InstrumentCollection containing BTCUSDT.

    Returns:
        InstrumentCollection: Collection with a single BTCUSDT instrument.
    """
    instrument = Instrument(
        venue=Venue.BINANCE_USDM,
        symbol="BTCUSDT",
        base="BTC",
        quote="USDT",
        code=0,
        instrument_type=InstrumentType.PERPETUAL,
        tick_size=0.01,
        lot_size=0.001,
    )
    return InstrumentCollection([instrument])


class TestBookTickerStreamUpdate:
    """Layer 1: Book ticker conversion."""

    def test_is_outdated(self) -> None:
        """Test is_outdated flags old updates."""
        update = BookTickerStreamUpdate(
            update_id=10,
            event_time=1,
            transaction_time=1,
            symbol="BTCUSDT",
            best_bid_price="1",
            best_bid_qty="1",
            best_ask_price="2",
            best_ask_qty="1",
        )

        assert update.is_outdated(10) is True
        assert update.is_outdated(9) is False

    def test_to_orderbook_msg(self) -> None:
        """Test orderbook message conversion."""
        update = BookTickerStreamUpdate(
            update_id=10,
            event_time=1,
            transaction_time=1,
            symbol="BTCUSDT",
            best_bid_price="1",
            best_bid_qty="1",
            best_ask_price="2",
            best_ask_qty="1",
        )
        msg = update.to_orderbook_msg(
            venue=Venue.BINANCE_USDM,
            instrument_collection=make_collection(),
        )

        assert msg.bids[0].price == 1.0
        assert msg.is_bbo is True


class TestDiffBookDepthStreamUpdate:
    """Layer 1: Diff depth conversion."""

    def test_is_outdated(self) -> None:
        """Test is_outdated flags old updates."""
        update = DiffBookDepthStreamUpdate(
            event_type="depthUpdate",
            event_time=1,
            transaction_time=1,
            symbol="BTCUSDT",
            first_update_id=1,
            final_update_id=10,
            prev_final_update_id=9,
            bids=[("1", "1")],
            asks=[("2", "1")],
        )

        assert update.is_outdated(10) is True
        assert update.is_outdated(9) is False

    def test_to_orderbook_msg(self) -> None:
        """Test orderbook conversion for diff depth updates."""
        update = DiffBookDepthStreamUpdate(
            event_type="depthUpdate",
            event_time=1,
            transaction_time=1,
            symbol="BTCUSDT",
            first_update_id=1,
            final_update_id=10,
            prev_final_update_id=9,
            bids=[("1", "1")],
            asks=[("2", "1")],
        )
        msg = update.to_orderbook_msg(
            venue=Venue.BINANCE_USDM,
            instrument_collection=make_collection(),
        )

        assert msg.bids[0].price == 1.0
        assert msg.is_snapshot is False


class TestTradeStreamUpdate:
    """Layer 1: Trade conversion."""

    def test_to_trade_msg(self) -> None:
        """Test trade update conversion to TradeMsg."""
        update = TradeStreamUpdate(
            event_time=1,
            transaction_time=2,
            symbol="BTCUSDT",
            trade_id=100,
            price="30000",
            quantity="0.1",
            is_buyer_maker=False,
        )
        msg = update.to_trade_msg(
            venue=Venue.BINANCE_USDM,
            instrument_collection=make_collection(),
        )

        assert msg.trades[0].is_buy is True
        assert msg.trades[0].price == 30000.0


class TestMarkPriceStreamUpdate:
    """Layer 1: Mark price conversion."""

    def test_to_ticker_msg(self) -> None:
        """Test mark price conversion to TickerMsg."""
        collection = make_collection()
        instrument = collection.instruments[0]
        update = MarkPriceStreamUpdate(
            event_time=1,
            symbol="BTCUSDT",
            mark_price="30000",
            index_price="29990",
            estimated_settle_price="0",
            funding_rate="0.0001",
            next_funding_time=123,
        )
        msg = update.to_ticker_msg(
            venue=Venue.BINANCE_USDM,
            instrument_collection=collection,
            instrument_to_open_interest_map={
                instrument: OpenInterestInfo(open_interest=1000.0)
            },
            instrument_to_ticker_stats_24h_map={
                instrument: TickerStats24h(price_chg_24h_pct=0.01, avg_volume_24h=5.0)
            },
        )

        assert msg.open_interest == 1000.0
        assert msg.price_chg_24h_pct == 0.01


class TestOrderUpdateStreamUpdate:
    """Layer 2: Order update conversion."""

    def test_to_order_msg(self) -> None:
        """Test order update conversion to ExecutionMsg."""
        update = OrderUpdateStreamUpdate(
            event_type="ORDER_TRADE_UPDATE",
            event_time=1,
            transaction_time=2,
            order={
                "s": "BTCUSDT",
                "T": 2,
                "i": 1,
                "L": "30000",
                "S": "BUY",
                "l": "0.1",
                "m": False,
                "c": "client_1",
            },
        )

        msg = update.to_order_msg(
            venue=Venue.BINANCE_USDM,
            symbol_map={"btcusdt": make_collection().instruments[0]},
        )

        assert msg.executions[0].order_id == "1"
        assert msg.executions[0].is_buy is True


class TestExecutionReportStreamUpdate:
    """Layer 2: Execution report conversion."""

    def test_to_execution_msg_filters_zero_qty(self) -> None:
        """Test zero-quantity executions return None."""
        update = ExecutionReportStreamUpdate(
            event_type="executionReport",
            event_time=1,
            transaction_time=2,
            order={"s": "BTCUSDT", "l": "0", "T": 2, "i": 1, "L": "0", "S": "BUY"},
        )

        msg = update.to_execution_msg(
            venue=Venue.BINANCE_USDM,
            symbol_map={"btcusdt": make_collection().instruments[0]},
        )

        assert msg is None

    def test_to_execution_msg_maps_fields(self) -> None:
        """Test execution report conversion to ExecutionMsg."""
        update = ExecutionReportStreamUpdate(
            event_type="executionReport",
            event_time=1,
            transaction_time=2,
            order={
                "s": "BTCUSDT",
                "l": "0.1",
                "T": 2,
                "i": 1,
                "L": "30000",
                "S": "BUY",
                "m": True,
                "n": "0.01",
                "c": "client_1",
            },
        )

        msg = update.to_execution_msg(
            venue=Venue.BINANCE_USDM,
            symbol_map={"btcusdt": make_collection().instruments[0]},
        )

        assert msg.executions[0].fee_paid == 0.01


class TestAccountUpdateStreamUpdate:
    """Layer 2: Account update conversion."""

    def test_to_account_msg(self) -> None:
        """Test account update conversion to AccountMsg."""
        update = AccountUpdateStreamUpdate(
            event_type="ACCOUNT_UPDATE",
            event_time=1,
            transaction_time=2,
            account_data={
                "B": [{"a": "USDT", "wb": "1000.0"}],
                "m": "1.0",
                "mm": "0.5",
                "up": "10.0",
            },
        )

        msg = update.to_account_msg(venue=Venue.BINANCE_USDM)

        assert msg.balance == 1000.0
        assert msg.initial_margin == 1.0


class TestPositionUpdateStreamUpdate:
    """Layer 2: Position update conversion."""

    def test_to_position_msg_maps_fields(self) -> None:
        """Test position update conversion to PositionMsg."""
        update = PositionUpdateStreamUpdate(
            event_type="ACCOUNT_UPDATE",
            event_time=1,
            transaction_time=2,
            account_data={
                "P": [
                    {
                        "s": "BTCUSDT",
                        "pa": "1.0",
                        "ep": "30000",
                    }
                ]
            },
        )

        msg = update.to_position_msg(
            venue=Venue.BINANCE_USDM,
            symbol_map={"btcusdt": make_collection().instruments[0]},
        )

        assert msg is not None
        assert msg.size == 1.0

    def test_to_position_msg_filters_zero_size(self) -> None:
        """Test position update returns None for zero size."""
        update = PositionUpdateStreamUpdate(
            event_type="ACCOUNT_UPDATE",
            event_time=1,
            transaction_time=2,
            account_data={"P": [{"s": "BTCUSDT", "pa": "0", "ep": "0"}]},
        )

        msg = update.to_position_msg(
            venue=Venue.BINANCE_USDM,
            symbol_map={"btcusdt": make_collection().instruments[0]},
        )

        assert msg is None

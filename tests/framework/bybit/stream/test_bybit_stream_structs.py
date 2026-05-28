"""
Tests for Bybit stream data structures.

Tests deserialization, field mapping, and edge cases for all Bybit stream messages.
"""

from __future__ import annotations

import msgspec
import pytest

from framework.base.common import (
    Asset,
    Instrument,
    InstrumentCollection,
    InstrumentType,
    Symbol,
    Venue,
)
from framework.base.stream.models import OrderTimeInForce, OrderbookLevel
from framework.base.tools import SimpleCache
from framework.bybit.stream.models import (
    BybitExecutionMsg,
    BybitOrderMsg,
    BybitOrderbookMsg,
    BybitPositionMsg,
    BybitTickerPublicMsg,
    BybitOrderbookPublicMsg,
    BybitTickerMsg,
    BybitTrade,
    BybitTradeMsg,
    BybitWalletMsg,
)


class TestBybitTickerStructs:
    decoder = msgspec.json.Decoder(BybitTickerPublicMsg)

    @pytest.mark.parametrize(
        "topic_suffix, mark_price, index_price, funding_rate",
        [
            ("BTCUSDT", 28180.0, 28179.9, 0.0001),
            ("ETHUSDT", 1900.5, 1898.3, -0.00025),
        ],
    )
    def test_snapshot_variants(
        self, topic_suffix, mark_price, index_price, funding_rate
    ):
        payload = {
            "topic": f"tickers.{topic_suffix}",
            "type": "snapshot",
            "data": {
                "symbol": topic_suffix,
                "tickDirection": "PlusTick",
                "price24HPcnt": 0.0123,
                "lastPrice": mark_price,
                "prevPrice24H": 27800.0,
                "highPrice24H": 29000.0,
                "lowPrice24H": 27000.0,
                "prevPrice1H": 28000.0,
                "markPrice": mark_price,
                "indexPrice": index_price,
                "openInterest": 12345.6,
                "openInterestValue": 1.23e7,
                "turnover24H": 5.67e8,
                "volume24H": 4.56e7,
                "nextFundingTime": 1700000000000,
                "fundingRate": funding_rate,
            },
        }

        msg = self.decoder.decode(msgspec.json.encode(payload))

        assert msg.topic == f"tickers.{topic_suffix}"
        assert msg.data.symbol == topic_suffix
        assert msg.data.mark_price == pytest.approx(mark_price)
        assert msg.data.index_price == pytest.approx(index_price)
        assert msg.data.funding_rate == pytest.approx(funding_rate)


class TestBybitOrderbookStructs:
    decoder = msgspec.json.Decoder(BybitOrderbookPublicMsg)

    @pytest.mark.parametrize(
        "levels, expected_bid, expected_ask",
        [
            (
                {
                    "b": [{"price": 28180.0, "size": 10.0}],
                    "a": [{"price": 28181.0, "size": 11.0}],
                },
                (28180.0, 10.0),
                (28181.0, 11.0),
            ),
            (
                {
                    "b": [{"price": 1900.5, "size": 5.0}],
                    "a": [{"price": 1901.0, "size": 4.0}],
                },
                (1900.5, 5.0),
                (1901.0, 4.0),
            ),
        ],
    )
    def test_delta_levels(self, levels, expected_bid, expected_ask):
        payload = {
            "topic": "orderbook.1.BTCUSDT",
            "type": "delta",
            "data": {
                "s": "BTCUSDT",
                "b": levels["b"],
                "a": levels["a"],
                "u": 1001,
                "seq": 10,
            },
        }

        msg = self.decoder.decode(msgspec.json.encode(payload))

        assert msg.topic == "orderbook.1.BTCUSDT"
        assert isinstance(msg.data.bids[0], OrderbookLevel)
        assert msg.data.bids[0].price == pytest.approx(expected_bid[0])
        assert msg.data.bids[0].size == pytest.approx(expected_bid[1])
        assert msg.data.asks[0].price == pytest.approx(expected_ask[0])
        assert msg.data.asks[0].size == pytest.approx(expected_ask[1])


class TestBybitTradeStructs:
    """Test Bybit trade message structures."""

    decoder_single = msgspec.json.Decoder(BybitTrade)
    decoder_public = msgspec.json.Decoder(BybitTradeMsg)

    def test_decode_single_trade(self):
        """Test decoding a single trade with field name mappings."""
        payload = {
            "T": 1234567890000,
            "S": "BTCUSDT",
            "s": "Buy",
            "v": 0.05,
            "p": 30000.0,
            "i": "trade_123",
            "seq": 7890,
        }

        msg = self.decoder_single.decode(msgspec.json.encode(payload))

        assert msg.time_ms == 1234567890000
        assert msg.symbol == "BTCUSDT"
        assert msg.side == "Buy"
        assert msg.size == pytest.approx(0.05)
        assert msg.price == pytest.approx(30000.0)
        assert msg.id == "trade_123"
        assert msg.seq == 7890

    def test_decode_public_trade_message(self):
        """Test decoding public trade message wrapper with list of trades."""
        payload = {
            "topic": "publicTrade.BTCUSDT",
            "type": "snapshot",
            "ts": 1234567890000,
            "data": [
                {
                    "T": 1234567890000,
                    "S": "BTCUSDT",
                    "s": "Buy",
                    "v": 0.05,
                    "p": 30000.0,
                    "i": "trade_1",
                    "seq": 100,
                },
                {
                    "T": 1234567891000,
                    "S": "BTCUSDT",
                    "s": "Sell",
                    "v": 0.03,
                    "p": 29999.0,
                    "i": "trade_2",
                    "seq": 101,
                },
            ],
        }

        msg = self.decoder_public.decode(msgspec.json.encode(payload))

        assert msg.topic == "publicTrade.BTCUSDT"
        assert msg.type == "snapshot"
        assert msg.ts == 1234567890000
        assert len(msg.data) == 2
        assert msg.data[0].side == "Buy"
        assert msg.data[1].side == "Sell"


class TestBybitPositionMsg:
    """Test Bybit position message deserialization."""

    decoder = msgspec.json.Decoder(BybitPositionMsg)

    def test_decode_valid_position(self):
        """Test decoding valid position with all fields."""
        payload = {
            "positionIdx": 0,
            "tradeMode": 0,
            "riskId": 1,
            "riskLimitValue": "2000000",
            "symbol": "BTCUSDT",
            "side": "Buy",
            "size": "0.5",
            "entryPrice": "30000.00",
            "leverage": "10",
            "positionValue": "15000.00",
            "positionBalance": "1500.00",
            "markPrice": "30100.00",
            "positionIm": "1500.00",
            "positionImByMp": "1500.00",
            "positionMm": "75.00",
            "positionMmByMp": "75.00",
            "takeProfit": "0",
            "stopLoss": "0",
            "trailingStop": "0",
            "unrealisedPnl": "50.00",
            "curRealisedPnl": "0.00",
            "cumRealisedPnl": "-10.00",
            "sessionAvgPrice": "30000.00",
            "createdTime": "1234567800000",
            "updatedTime": "1234567890000",
            "tpslMode": "Full",
            "liqPrice": "27000.00",
            "bustPrice": "26500.00",
            "category": "linear",
            "positionStatus": "Normal",
            "adlRankIndicator": 2,
            "autoAddMargin": 0,
            "leverageSysUpdatedTime": "1234567000000",
            "mmrSysUpdatedTime": "1234567000000",
            "seq": 123456,
            "isReduceOnly": False,
        }

        msg = self.decoder.decode(msgspec.json.encode(payload))

        # Test key fields
        assert msg.symbol == "BTCUSDT"
        assert msg.side == "Buy"
        assert msg.size == "0.5"
        assert msg.entry_price == "30000.00"
        assert msg.position_idx == 0
        assert msg.trade_mode == 0
        assert msg.leverage == "10"
        assert msg.unrealised_pnl == "50.00"
        assert msg.cum_realised_pnl == "-10.00"
        assert msg.is_reduce_only is False

    def test_decode_position_with_zero_size(self):
        """Test decoding position with zero size (closed position)."""
        payload = {
            "positionIdx": 0,
            "tradeMode": 0,
            "riskId": 1,
            "riskLimitValue": "2000000",
            "symbol": "ETHUSDT",
            "side": "None",
            "size": "0",
            "entryPrice": "0",
            "leverage": "10",
            "positionValue": "0",
            "positionBalance": "0",
            "markPrice": "1900.00",
            "positionIm": "0",
            "positionImByMp": "0",
            "positionMm": "0",
            "positionMmByMp": "0",
            "takeProfit": "0",
            "stopLoss": "0",
            "trailingStop": "0",
            "unrealisedPnl": "0",
            "curRealisedPnl": "0",
            "cumRealisedPnl": "100.50",
            "sessionAvgPrice": "0",
            "createdTime": "1234567800000",
            "updatedTime": "1234567890000",
            "tpslMode": "Full",
            "liqPrice": "0",
            "bustPrice": "0",
            "category": "linear",
            "positionStatus": "Normal",
            "adlRankIndicator": 0,
            "autoAddMargin": 0,
            "leverageSysUpdatedTime": "1234567000000",
            "mmrSysUpdatedTime": "1234567000000",
            "seq": 123457,
            "isReduceOnly": False,
        }

        msg = self.decoder.decode(msgspec.json.encode(payload))

        assert msg.symbol == "ETHUSDT"
        assert msg.side == "None"
        assert msg.size == "0"
        assert msg.entry_price == "0"


class TestBybitOrderMsg:
    """Test Bybit order message deserialization."""

    decoder = msgspec.json.Decoder(BybitOrderMsg)

    def test_decode_valid_order(self):
        """Test decoding valid order with all fields."""
        payload = {
            "symbol": "BTCUSDT",
            "orderId": "order_123456",
            "side": "Buy",
            "orderType": "Limit",
            "cancelType": "",
            "price": "30000.00",
            "qty": "0.01",
            "timeInForce": "GTC",
            "orderStatus": "New",
            "orderLinkId": "client_123",
            "lastPriceOnCreated": "30050.00",
            "reduceOnly": False,
            "leavesQty": "0.01",
            "leavesValue": "300.00",
            "cumExecQty": "0",
            "cumExecValue": "0",
            "avgPrice": "0",
            "blockTradeId": "",
            "positionIdx": 0,
            "cumExecFee": "0",
            "closedPnl": "0",
            "createdTime": "1234567890000",
            "updatedTime": "1234567890000",
            "rejectReason": "",
            "stopOrderType": "",
            "triggerDirection": 0,
            "triggerBy": "",
            "closeOnTrigger": False,
            "category": "linear",
            "placeType": "",
        }

        msg = self.decoder.decode(msgspec.json.encode(payload))

        # Test key fields with camelCase mapping
        assert msg.symbol == "BTCUSDT"
        assert msg.order_id == "order_123456"
        assert msg.side == "Buy"
        assert msg.order_type == "Limit"
        assert msg.price == "30000.00"
        assert msg.qty == "0.01"
        assert msg.time_in_force == "GTC"
        assert msg.order_status == "New"
        assert msg.order_link_id == "client_123"
        assert msg.reduce_only is False
        assert msg.leaves_qty == "0.01"
        assert msg.cum_exec_qty == "0"

    def test_decode_order_partially_filled(self):
        """Test decoding partially filled order."""
        payload = {
            "symbol": "ETHUSDT",
            "orderId": "order_789",
            "side": "Sell",
            "orderType": "Limit",
            "cancelType": "",
            "price": "1900.00",
            "qty": "1.0",
            "timeInForce": "GTC",
            "orderStatus": "PartiallyFilled",
            "orderLinkId": "client_789",
            "lastPriceOnCreated": "1900.00",
            "reduceOnly": False,
            "leavesQty": "0.6",
            "leavesValue": "1140.00",
            "cumExecQty": "0.4",
            "cumExecValue": "760.00",
            "avgPrice": "1900.00",
            "blockTradeId": "",
            "positionIdx": 0,
            "cumExecFee": "0.76",
            "closedPnl": "0",
            "createdTime": "1234567890000",
            "updatedTime": "1234567900000",
            "rejectReason": "",
            "stopOrderType": "",
            "triggerDirection": 0,
            "triggerBy": "",
            "closeOnTrigger": False,
            "category": "linear",
            "placeType": "",
        }

        msg = self.decoder.decode(msgspec.json.encode(payload))

        assert msg.order_status == "PartiallyFilled"
        assert msg.leaves_qty == "0.6"
        assert msg.cum_exec_qty == "0.4"
        assert msg.avg_price == "1900.00"


class TestBybitExecutionMsg:
    """Test Bybit execution message deserialization."""

    decoder = msgspec.json.Decoder(BybitExecutionMsg)

    def test_decode_valid_execution(self):
        """Test decoding valid execution with all fields."""
        payload = {
            "category": "linear",
            "symbol": "BTCUSDT",
            "closedSize": "0",
            "execFee": "0.03",
            "execId": "exec_123456",
            "execPrice": "30000.00",
            "execQty": "0.01",
            "execType": "Trade",
            "execValue": "300.00",
            "feeRate": "0.0001",
            "markPrice": "30000.00",
            "indexPrice": "29999.50",
            "underlyingPrice": "29999.00",
            "leavesQty": "0",
            "orderId": "order_123",
            "orderLinkId": "client_123",
            "orderPrice": "30000.00",
            "orderQty": "0.01",
            "orderType": "Limit",
            "stopOrderType": "",
            "side": "Buy",
            "execTime": "1234567890000",
            "isLeverage": "0",
            "isMaker": True,
            "seq": 123456,
            "marketUnit": "",
            "execPnl": "0",
            "createType": "CreateByUser",
        }

        msg = self.decoder.decode(msgspec.json.encode(payload))

        # Test key fields with camelCase mapping
        assert msg.category == "linear"
        assert msg.symbol == "BTCUSDT"
        assert msg.exec_id == "exec_123456"
        assert msg.exec_price == "30000.00"
        assert msg.exec_qty == "0.01"
        assert msg.exec_fee == "0.03"
        assert msg.exec_type == "Trade"
        assert msg.order_id == "order_123"
        assert msg.order_link_id == "client_123"
        assert msg.side == "Buy"
        assert msg.is_maker is True
        assert msg.fee_rate == "0.0001"

    def test_decode_execution_taker(self):
        """Test decoding taker execution."""
        payload = {
            "category": "linear",
            "symbol": "ETHUSDT",
            "closedSize": "0",
            "execFee": "0.19",
            "execId": "exec_789",
            "execPrice": "1900.00",
            "execQty": "0.1",
            "execType": "Trade",
            "execValue": "190.00",
            "feeRate": "0.001",
            "markPrice": "1900.00",
            "indexPrice": "1899.50",
            "underlyingPrice": "1899.00",
            "leavesQty": "0",
            "orderId": "order_789",
            "orderLinkId": "client_789",
            "orderPrice": "1900.00",
            "orderQty": "0.1",
            "orderType": "Market",
            "stopOrderType": "",
            "side": "Sell",
            "execTime": "1234567891000",
            "isLeverage": "0",
            "isMaker": False,
            "seq": 123457,
            "marketUnit": "",
            "execPnl": "0",
            "createType": "CreateByUser",
        }

        msg = self.decoder.decode(msgspec.json.encode(payload))

        assert msg.is_maker is False
        assert msg.order_type == "Market"
        assert msg.fee_rate == "0.001"


class TestBybitTickerConversion:
    """Layer 2: Ticker conversion behavior."""

    def test_to_ticker_msg_maps_fields(self):
        """Test BybitTickerMsg converts to TickerMsg."""
        instrument = Instrument(
            venue=Venue.BYBIT,
            symbol=Symbol("BTCUSDT"),
            base=Asset("BTC"),
            quote=Asset("USDT"),
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        collection = InstrumentCollection([instrument])
        ticker = BybitTickerMsg(
            symbol="BTCUSDT",
            tick_direction="PlusTick",
            price_24h_pcnt=0.01,
            last_price=30000.0,
            prev_price_24h=29500.0,
            high_price_24h=31000.0,
            low_price_24h=29000.0,
            prev_price_1h=29900.0,
            mark_price=30000.0,
            index_price=29990.0,
            open_interest=1000.0,
            open_interest_value=1.0,
            turnover_24h=2.0,
            volume_24h=300.0,
            next_funding_time=1234567890,
            funding_rate=0.0001,
        )

        msg = ticker.to_ticker_msg(
            venue=Venue.BYBIT,
            instrument_collection=collection,
            exch_time_ns=1,
            is_snapshot=True,
        )

        assert msg.instrument == instrument
        assert msg.mark_price == 30000.0
        assert msg.index_price == 29990.0


class TestBybitOrderbookConversion:
    """Layer 2: Orderbook conversion behavior."""

    def test_to_orderbook_msg_sorts_levels(self):
        """Test BybitOrderbookMsg sorts bids/asks by price."""
        instrument = Instrument(
            venue=Venue.BYBIT,
            symbol=Symbol("BTCUSDT"),
            base=Asset("BTC"),
            quote=Asset("USDT"),
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        collection = InstrumentCollection([instrument])

        orderbook = BybitOrderbookMsg(
            symbol="BTCUSDT",
            bids=[
                OrderbookLevel(price=30000.0, size=1.0),
                OrderbookLevel(price=29900.0, size=2.0),
            ],
            asks=[
                OrderbookLevel(price=30100.0, size=1.0),
                OrderbookLevel(price=30050.0, size=1.5),
            ],
            update_id=1,
            seq=1,
        )

        msg = orderbook.to_orderbook_msg(
            venue=Venue.BYBIT,
            instrument_collection=collection,
            is_bbo=False,
            is_snapshot=True,
            exch_time_ns=1,
        )

        assert msg.bids[0].price == 29900.0
        assert msg.asks[0].price == 30050.0


class TestBybitTradeConversion:
    """Layer 2: Trade conversion behavior."""

    def test_to_trade_msg_deduplicates(self):
        """Test duplicate sequence trades are filtered."""
        instrument = Instrument(
            venue=Venue.BYBIT,
            symbol=Symbol("BTCUSDT"),
            base=Asset("BTC"),
            quote=Asset("USDT"),
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        collection = InstrumentCollection([instrument])
        cache = SimpleCache()

        public_msg = BybitTradeMsg(
            topic="publicTrade.BTCUSDT",
            type="snapshot",
            ts=123,
            data=[
                BybitTrade(
                    time_ms=1,
                    symbol="BTCUSDT",
                    side="Buy",
                    size=1.0,
                    price=100.0,
                    id="1",
                    seq=1,
                ),
                BybitTrade(
                    time_ms=2,
                    symbol="BTCUSDT",
                    side="Buy",
                    size=2.0,
                    price=101.0,
                    id="2",
                    seq=1,
                ),
            ],
        )

        msg = public_msg.to_trade_msg(
            venue=Venue.BYBIT,
            instrument_collection=collection,
            symbol_to_seq_cache=cache,
        )

        assert msg is not None
        assert len(msg.trades) == 1

    def test_to_trade_msg_raises_when_filtered(self):
        """Test to_trade_msg raises when all trades are filtered."""
        instrument = Instrument(
            venue=Venue.BYBIT,
            symbol=Symbol("BTCUSDT"),
            base=Asset("BTC"),
            quote=Asset("USDT"),
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        collection = InstrumentCollection([instrument])
        cache = SimpleCache()
        cache.is_higher("BTCUSDT_1", 1)

        public_msg = BybitTradeMsg(
            topic="publicTrade.BTCUSDT",
            type="snapshot",
            ts=123,
            data=[
                BybitTrade(
                    time_ms=1,
                    symbol="BTCUSDT",
                    side="Buy",
                    size=1.0,
                    price=100.0,
                    id="1",
                    seq=1,
                )
            ],
        )

        with pytest.raises(ValueError):
            public_msg.to_trade_msg(
                venue=Venue.BYBIT,
                instrument_collection=collection,
                symbol_to_seq_cache=cache,
            )


class TestBybitPositionConversion:
    """Layer 2: Position conversion behavior."""

    def test_to_position_msg_maps_fields(self):
        """Test BybitPositionMsg converts to PositionMsg."""
        instrument = Instrument(
            venue=Venue.BYBIT,
            symbol=Symbol("BTCUSDT"),
            base=Asset("BTC"),
            quote=Asset("USDT"),
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        collection = InstrumentCollection([instrument])

        position = BybitPositionMsg(
            position_idx=0,
            trade_mode=0,
            risk_id=1,
            risk_limit_value="0",
            symbol="BTCUSDT",
            side="Buy",
            size="1.5",
            entry_price="30000",
            leverage="10",
            position_value="0",
            position_balance="0",
            mark_price="0",
            position_im="0",
            position_im_by_mp="0",
            position_mm="0",
            position_mm_by_mp="0",
            take_profit="0",
            stop_loss="0",
            trailing_stop="0",
            unrealised_pnl="0",
            cur_realised_pnl="0",
            cum_realised_pnl="0",
            session_avg_price="0",
            created_time="0",
            updated_time="0",
            tpsl_mode="Full",
            liq_price="0",
            bust_price="0",
            category="linear",
            position_status="Normal",
            adl_rank_indicator=0,
            auto_add_margin=0,
            leverage_sys_updated_time="0",
            mmr_sys_updated_time="0",
            seq=1,
            is_reduce_only=False,
        )

        msg = position.to_position_msg(
            venue=Venue.BYBIT,
            instrument_collection=collection,
            exch_time_ns=1,
            is_snapshot=False,
        )

        assert msg is not None
        assert msg.size == 1.5
        assert msg.is_long is True

    def test_to_position_msg_ignores_zero_size(self):
        """Test zero size positions return None."""
        instrument = Instrument(
            venue=Venue.BYBIT,
            symbol=Symbol("BTCUSDT"),
            base=Asset("BTC"),
            quote=Asset("USDT"),
            code=0,
            instrument_type=InstrumentType.PERPETUAL,
            tick_size=0.01,
            lot_size=0.001,
        )
        collection = InstrumentCollection([instrument])

        position = BybitPositionMsg(
            position_idx=0,
            trade_mode=0,
            risk_id=1,
            risk_limit_value="0",
            symbol="BTCUSDT",
            side="Buy",
            size="0",
            entry_price="0",
            leverage="10",
            position_value="0",
            position_balance="0",
            mark_price="0",
            position_im="0",
            position_im_by_mp="0",
            position_mm="0",
            position_mm_by_mp="0",
            take_profit="0",
            stop_loss="0",
            trailing_stop="0",
            unrealised_pnl="0",
            cur_realised_pnl="0",
            cum_realised_pnl="0",
            session_avg_price="0",
            created_time="0",
            updated_time="0",
            tpsl_mode="Full",
            liq_price="0",
            bust_price="0",
            category="linear",
            position_status="Normal",
            adl_rank_indicator=0,
            auto_add_margin=0,
            leverage_sys_updated_time="0",
            mmr_sys_updated_time="0",
            seq=1,
            is_reduce_only=False,
        )

        msg = position.to_position_msg(
            venue=Venue.BYBIT,
            instrument_collection=collection,
            exch_time_ns=1,
            is_snapshot=False,
        )

        assert msg is None


class TestBybitOrderConversion:
    """Layer 2: Order conversion behavior."""

    def test_to_order_maps_fields(self):
        """Test BybitOrderMsg converts to Order."""
        order_msg = BybitOrderMsg(
            symbol="BTCUSDT",
            order_id="order_1",
            side="Buy",
            order_type="Limit",
            cancel_type="",
            price="30000",
            qty="2",
            time_in_force="GTC",
            order_status="New",
            order_link_id="client_1",
            last_price_on_created="0",
            reduce_only=False,
            leaves_qty="0",
            leaves_value="0",
            cum_exec_qty="1",
            cum_exec_value="0",
            avg_price="0",
            block_trade_id="",
            position_idx=0,
            cum_exec_fee="0",
            closed_pnl="0",
            created_time="1",
            updated_time="1",
            reject_reason="",
            stop_order_type="",
            trigger_direction=0,
            trigger_by="",
            close_on_trigger=False,
            category="linear",
            place_type="",
        )

        order = order_msg.to_order()

        assert order.order_id == "order_1"
        assert order.tif == OrderTimeInForce.GTC
        assert order.size_remaining == 1.0


class TestBybitExecutionConversion:
    """Layer 2: Execution conversion behavior."""

    def test_to_execution_maps_fields(self):
        """Test BybitExecutionMsg converts to Execution."""
        exec_msg = BybitExecutionMsg(
            category="linear",
            symbol="BTCUSDT",
            closed_size="0",
            exec_fee="0.01",
            exec_id="exec_1",
            exec_price="30000",
            exec_qty="1",
            exec_type="Trade",
            exec_value="0",
            fee_rate="0",
            mark_price="0",
            index_price="0",
            underlying_price="0",
            leaves_qty="0",
            order_id="order_1",
            order_link_id="client_1",
            order_price="30000",
            order_qty="1",
            order_type="Limit",
            stop_order_type="",
            side="Buy",
            exec_time="1",
            is_leverage="0",
            is_maker=True,
            seq=1,
            market_unit="",
            exec_pnl="0",
            create_type="CreateByUser",
        )

        execution = exec_msg.to_execution()

        assert execution.order_id == "order_1"
        assert execution.is_maker is True
        assert execution.fee_paid == 0.01


class TestBybitWalletConversion:
    """Layer 2: Wallet conversion behavior."""

    def test_to_account_msg_maps_fields(self):
        """Test BybitWalletMsg converts to AccountMsg."""
        wallet = BybitWalletMsg(
            total_equity="1000",
            account_im_rate="0.1",
            account_mm_rate="0.05",
            total_perp_upl="10",
        )

        msg = wallet.to_account_msg(
            venue=Venue.BYBIT,
            exch_time_ns=1,
            is_snapshot=False,
        )

        assert msg.balances[msg.instrument].amount == 1000.0
        assert msg.initial_margin == 0.1

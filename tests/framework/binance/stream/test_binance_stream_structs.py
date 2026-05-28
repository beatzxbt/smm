"""Tests for Binance stream raw struct decoding.

Layer 1 validates primitive market-data structs decode the expected fields.
Layer 2 validates private/tagged structs and union routing decode correctly.
"""

from __future__ import annotations

import msgspec

from framework.binance.stream.models import (
    AccountUpdateStreamUpdate,
    BookTickerStreamUpdate,
    DiffBookDepthStreamUpdate,
    ExecutionReportStreamUpdate,
    MarkPriceStreamUpdate,
    OrderUpdateStreamUpdate,
    PositionUpdateStreamUpdate,
    TickerStats24hStreamUpdate,
    TradeStreamUpdate,
)


class TestBinanceMarketStructDecoding:
    """Layer 1: Primitive market stream struct decoding."""

    def test_book_ticker_decodes_fields(self) -> None:
        """Decode book ticker payload into the expected typed struct fields."""
        payload = {
            "u": 10,
            "E": 1,
            "T": 1,
            "s": "BTCUSDT",
            "b": "1.0",
            "B": "2.0",
            "a": "3.0",
            "A": "4.0",
        }

        decoded = msgspec.json.decode(
            msgspec.json.encode(payload), type=BookTickerStreamUpdate
        )

        assert decoded.update_id == 10
        assert decoded.symbol == "BTCUSDT"
        assert decoded.best_bid_price == "1.0"
        assert decoded.best_ask_qty == "4.0"

    def test_diff_depth_decodes_fields(self) -> None:
        """Decode diff-depth payload into the expected typed struct fields."""
        payload = {
            "e": "depthUpdate",
            "E": 1,
            "T": 1,
            "s": "BTCUSDT",
            "U": 1,
            "u": 2,
            "pu": 0,
            "b": [["1.0", "2.0"]],
            "a": [["3.0", "4.0"]],
        }

        decoded = msgspec.json.decode(
            msgspec.json.encode(payload), type=DiffBookDepthStreamUpdate
        )

        assert decoded.event_type == "depthUpdate"
        assert decoded.first_update_id == 1
        assert decoded.final_update_id == 2
        assert decoded.bids[0] == ("1.0", "2.0")

    def test_trade_update_decodes_fields(self) -> None:
        """Decode trade payload into the expected typed struct fields."""
        payload = {
            "e": "trade",
            "E": 1,
            "T": 2,
            "s": "BTCUSDT",
            "t": 100,
            "p": "30000",
            "q": "0.1",
            "X": "MARKET",
            "m": False,
        }

        decoded = msgspec.json.decode(
            msgspec.json.encode(payload), type=TradeStreamUpdate
        )

        assert decoded.event_type == "trade"
        assert decoded.transaction_time == 2
        assert decoded.trade_id == 100
        assert decoded.trade_type == "MARKET"
        assert decoded.is_buyer_maker is False

    def test_mark_price_decodes_fields(self) -> None:
        """Decode mark-price payload into the expected typed struct fields."""
        payload = {
            "E": 1,
            "s": "BTCUSDT",
            "p": "30000",
            "i": "29990",
            "P": "0",
            "r": "0.0001",
            "T": 123,
        }

        decoded = msgspec.json.decode(
            msgspec.json.encode(payload), type=MarkPriceStreamUpdate
        )

        assert decoded.event_time == 1
        assert decoded.symbol == "BTCUSDT"
        assert decoded.mark_price == "30000"
        assert decoded.next_funding_time == 123

    def test_ticker_stats_24h_decodes_and_converts(self) -> None:
        """Decode ticker-stats payload and convert to helper stats struct."""
        payload = {
            "E": 1,
            "s": "BTCUSDT",
            "p": "10.0",
            "P": "0.5",
            "v": "1000.0",
            "q": "2000.0",
        }

        decoded = msgspec.json.decode(
            msgspec.json.encode(payload), type=TickerStats24hStreamUpdate
        )
        stats = decoded.to_ticker_stats_24h()

        assert decoded.symbol == "BTCUSDT"
        assert stats.price_chg_24h_pct == 0.5
        assert stats.avg_volume_24h == 1000.0


class TestBinancePrivateStructDecoding:
    """Layer 2: Composite/tagged private stream struct decoding."""

    def test_order_update_decodes_with_tagged_type(self) -> None:
        """Decode ORDER_TRADE_UPDATE payload into tagged order update struct."""
        payload = {
            "e": "ORDER_TRADE_UPDATE",
            "E": 1,
            "T": 2,
            "o": {
                "s": "BTCUSDT",
                "c": "client_1",
                "S": "BUY",
                "o": "LIMIT",
                "f": "GTC",
                "q": "1.0",
                "p": "30000",
                "ap": "30000",
                "l": "0.1",
                "z": "0.1",
                "L": "30000",
                "n": "0.01",
                "N": "USDT",
                "T": 2,
                "t": 1,
                "m": True,
                "i": 1,
                "ps": "BOTH",
                "X": "TRADE",
                "R": False,
            },
        }

        decoded = msgspec.json.decode(
            msgspec.json.encode(payload), type=OrderUpdateStreamUpdate
        )

        assert decoded.event_time == 1
        assert decoded.order.symbol == "BTCUSDT"
        assert decoded.order.status == "TRADE"
        assert decoded.order.order_id == 1

    def test_account_update_decodes_with_tagged_type(self) -> None:
        """Decode ACCOUNT_UPDATE payload into tagged account update struct."""
        payload = {
            "e": "ACCOUNT_UPDATE",
            "E": 1,
            "T": 2,
            "a": {
                "B": [{"a": "USDT", "wb": "1000.0", "cw": "1000.0"}],
                "P": [
                    {
                        "s": "BTCUSDT",
                        "pa": "1.0",
                        "ep": "30000",
                        "cr": "0.0",
                        "up": "10.0",
                        "ps": "BOTH",
                    }
                ],
                "m": "1.0",
                "mm": "0.5",
                "u": "10.0",
                "up": "10.0",
            },
        }

        decoded = msgspec.json.decode(
            msgspec.json.encode(payload), type=AccountUpdateStreamUpdate
        )

        assert decoded.event_time == 1
        assert decoded.account_data.balances[0].asset == "USDT"
        assert decoded.account_data.positions[0].symbol == "BTCUSDT"
        assert decoded.account_data.maintenance_margin == "1.0"

    def test_position_update_decodes_fields(self) -> None:
        """Decode position update payload into non-tagged position update struct."""
        payload = {
            "e": "ACCOUNT_UPDATE",
            "E": 1,
            "T": 2,
            "a": {
                "B": [{"a": "USDT", "wb": "1000.0", "cw": "1000.0"}],
                "P": [
                    {
                        "s": "BTCUSDT",
                        "pa": "1.0",
                        "ep": "30000",
                        "cr": "0.0",
                        "up": "10.0",
                        "ps": "BOTH",
                    }
                ],
                "m": "1.0",
                "mm": "0.5",
                "u": "10.0",
                "up": "10.0",
            },
        }

        decoded = msgspec.json.decode(
            msgspec.json.encode(payload), type=PositionUpdateStreamUpdate
        )

        assert decoded.event_type == "ACCOUNT_UPDATE"
        assert decoded.account_data.positions[0].position_amount == "1.0"

    def test_execution_report_decodes_fields(self) -> None:
        """Decode execution-report payload into non-tagged execution report struct."""
        payload = {
            "e": "executionReport",
            "E": 1,
            "T": 2,
            "o": {
                "s": "BTCUSDT",
                "c": "client_1",
                "S": "BUY",
                "o": "LIMIT",
                "f": "GTC",
                "q": "1.0",
                "p": "30000",
                "ap": "30000",
                "l": "0.1",
                "z": "0.1",
                "L": "30000",
                "n": "0.01",
                "N": "USDT",
                "T": 2,
                "t": 1,
                "m": True,
                "i": 1,
                "ps": "BOTH",
                "X": "TRADE",
                "R": False,
            },
        }

        decoded = msgspec.json.decode(
            msgspec.json.encode(payload), type=ExecutionReportStreamUpdate
        )

        assert decoded.event_type == "executionReport"
        assert decoded.order.order_id == 1
        assert decoded.order.last_exec_qty == "0.1"


class TestBinancePrivateUnionDecoding:
    """Layer 3: Mini-integration for private tagged union routing."""

    decoder = msgspec.json.Decoder(OrderUpdateStreamUpdate | AccountUpdateStreamUpdate)

    def test_union_decoder_routes_order_update(self) -> None:
        """Decode order payload and assert union returns order update type."""
        payload = {
            "e": "ORDER_TRADE_UPDATE",
            "E": 1,
            "T": 2,
            "o": {
                "s": "BTCUSDT",
                "c": "client_1",
                "S": "BUY",
                "o": "LIMIT",
                "f": "GTC",
                "q": "1.0",
                "p": "30000",
                "ap": "30000",
                "l": "0.1",
                "z": "0.1",
                "L": "30000",
                "n": "0.01",
                "N": "USDT",
                "T": 2,
                "t": 1,
                "m": True,
                "i": 1,
                "ps": "BOTH",
                "X": "TRADE",
                "R": False,
            },
        }

        decoded = self.decoder.decode(msgspec.json.encode(payload))

        assert isinstance(decoded, OrderUpdateStreamUpdate)
        assert decoded.order.symbol == "BTCUSDT"

    def test_union_decoder_routes_account_update(self) -> None:
        """Decode account payload and assert union returns account update type."""
        payload = {
            "e": "ACCOUNT_UPDATE",
            "E": 1,
            "T": 2,
            "a": {
                "B": [{"a": "USDT", "wb": "1000.0", "cw": "1000.0"}],
                "P": [],
                "m": "1.0",
                "mm": "0.5",
                "u": "10.0",
                "up": "10.0",
            },
        }

        decoded = self.decoder.decode(msgspec.json.encode(payload))

        assert isinstance(decoded, AccountUpdateStreamUpdate)
        assert decoded.account_data.balances[0].asset == "USDT"

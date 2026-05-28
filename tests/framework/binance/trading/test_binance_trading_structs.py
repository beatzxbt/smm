"""tests.framework.binance.trading.test_binance_trading_structs"""

from __future__ import annotations

import msgspec
import pytest

from framework.binance.trading.models import (
    BinanceHttpCancelAllOrdersResponse,
    BinanceHttpOrderbookResponse,
    BinanceHttpTradeResponse,
    BinanceHttpExchangeInformationResponse,
    BinanceWsCreateOrderResult,
    BinanceWsOrderResponse,
)


class TestBinanceWsOrderResponse:
    """Layer 1: WS response decoding."""

    decoder = msgspec.json.Decoder(BinanceWsOrderResponse[BinanceWsCreateOrderResult])

    @pytest.mark.parametrize("status", [0, 200])
    def test_is_successful_status_codes(self, status: int) -> None:
        """Test is_successful returns True for status 0/200.

        Args:
            status: Status code under test.
        """
        payload = {
            "id": "req-1",
            "status": status,
            "result": {
                "orderId": 1,
                "symbol": "BTCUSDT",
                "status": "NEW",
                "clientOrderId": "client_1",
                "price": "30000",
                "avgPrice": "0",
                "origQty": "1",
                "executedQty": "0",
                "cumQty": "0",
                "cumQuote": "0",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "reduceOnly": False,
                "closePosition": False,
                "side": "BUY",
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "origType": "LIMIT",
                "priceMatch": "NONE",
                "selfTradePreventionMode": "NONE",
                "goodTillDate": 0,
                "updateTime": 0,
            },
        }

        msg = self.decoder.decode(msgspec.json.encode(payload))
        assert msg.is_successful is True
        assert msg.result.order_id == 1


class TestBinanceHttpResponses:
    """Layer 1: HTTP response decoding."""

    def test_cancel_all_orders_is_successful(self) -> None:
        """Test cancel-all response success detection."""
        resp = BinanceHttpCancelAllOrdersResponse(code=200, msg="ok")
        assert resp.is_successful is True

    def test_orderbook_response_decoding(self) -> None:
        """Test orderbook response decoding uses expected fields."""
        payload = {
            "lastUpdateId": 1,
            "E": 2,
            "T": 3,
            "bids": [["30000", "1"]],
            "asks": [["30001", "2"]],
        }
        decoded = msgspec.json.Decoder(BinanceHttpOrderbookResponse).decode(
            msgspec.json.encode(payload)
        )

        assert decoded.last_update_id == 1
        assert decoded.bids[0][0] == "30000"

    def test_trade_response_decoding(self) -> None:
        """Test trade response decoding maps expected fields."""
        payload = {
            "id": 1,
            "price": "30000",
            "qty": "0.1",
            "quoteQty": "0",
            "time": 1,
            "isBuyerMaker": False,
        }
        decoded = msgspec.json.Decoder(BinanceHttpTradeResponse).decode(
            msgspec.json.encode(payload)
        )

        assert decoded.id == 1
        assert decoded.price == "30000"

    def test_exchange_info_decoding(self) -> None:
        """Test exchange info response decoding maps filters."""
        payload = {
            "symbols": [
                {
                    "status": "TRADING",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "underlyingType": "COIN",
                    "filters": [
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0",
                            "maxPrice": "0",
                            "tickSize": "0.1",
                            "minQty": None,
                            "maxQty": None,
                            "stepSize": None,
                        }
                    ],
                }
            ]
        }
        decoded = msgspec.json.Decoder(BinanceHttpExchangeInformationResponse).decode(
            msgspec.json.encode(payload)
        )

        assert decoded.symbols[0].base_asset == "BTC"

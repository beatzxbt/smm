import msgspec
import pytest

from framework.bybit.trading.models import (
    BybitWsCreateOrderResult,
    BybitWsOrderResponse,
)


class TestBybitTradingStructs:
    decoder = msgspec.json.Decoder(BybitWsOrderResponse[BybitWsCreateOrderResult])
    payload_core = {
        "orderId": 123456,
        "symbol": "BTCUSDT",
        "status": "Created",
        "clientOrderId": "test123",
        "price": "30000",
        "avgPrice": "0",
        "origQty": "0.01",
        "executedQty": "0",
        "cumQty": "0",
        "cumQuote": "0",
        "timeInForce": "GTC",
        "type": "Limit",
        "reduceOnly": False,
        "closePosition": False,
        "side": "Buy",
        "positionSide": "Both",
        "stopPrice": "0",
        "workingType": "MarkPrice",
        "priceProtect": False,
        "origType": "Limit",
        "priceMatch": "None",
        "selfTradePreventionMode": "None",
        "goodTillDate": 0,
        "updateTime": 1697670000000,
    }

    @pytest.mark.parametrize("status_code", [0, 200])
    def test_decode_success_status(self, status_code: int):
        payload = {
            "id": "req-abc",
            "status": status_code,
            "result": self.payload_core,
        }
        msg = self.decoder.decode(msgspec.json.encode(payload))

        assert msg.id == "req-abc"
        assert msg.status == status_code
        assert msg.is_successful is True
        assert msg.result.order_id == 123456
        assert msg.result.symbol == "BTCUSDT"
        assert msg.result.time_in_force == "GTC"

    def test_decode_failure_status(self):
        payload = {
            "id": "req-fail",
            "status": 400,
            "result": self.payload_core,
        }
        msg = self.decoder.decode(msgspec.json.encode(payload))

        assert msg.id == "req-fail"
        assert msg.status == 400
        assert msg.is_successful is False

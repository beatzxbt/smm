from typing import Dict, List

from frameworks.exchange.base.types import Order, OrderType
from frameworks.exchange.base.formats import Formats
from frameworks.exchange.bybit.types import (
    BybitSideConverter,
    BybitOrderTypeConverter,
    BybitTimeInForceConverter,
    BybitPositionDirectionConverter
)


class BybitFormats(Formats):
    def __init__(self) -> None:
        super().__init__(
            convert_side=BybitSideConverter(),
            convert_order_type=BybitOrderTypeConverter(),
            convert_time_in_force=BybitTimeInForceConverter(),
            convert_position_direction=BybitPositionDirectionConverter()
        )
        self.base_payload = {"category": "linear"}

    def create_order(self, order):
        format = {
            **self.base_payload,
            "symbol": order.symbol,
            "side": self.convert_side.to_str(order.side),
            "orderType": self.convert_order_type.to_str(order.orderType),
            "timeInForce": self.convert_tif.to_str(order.timeInForce),
            "qty": str(order.size),
            **({"orderLinkId": order.clientOrderId} if order.clientOrderId else {}),
        }

        match order.orderType:
            case OrderType.MARKET:
                return format

            case OrderType.LIMIT:
                format["price"] = str(order.price)

        return format

    def batch_create_orders(self, orders: List[Order]) -> Dict:
        batched_orders = []

        for order in orders:
            single_order = self.create_order(order)
            del single_order["category"]
            batched_orders.append(order)

        format = {**self.base_payload, "request": batched_orders}

        return format

    def amend_order(self, order):
        return {
            **self.base_payload,
            "price": str(order.price),
            "qty": str(order.size),
            **({"orderId": order.orderId} if order.orderId else {}),
            **({"orderLinkId": order.clientOrderId} if order.clientOrderId else {}),
        }

    def batch_amend_orders(self, orders: List[Order]) -> Dict:
        batched_amends = []

        for order in orders:
            single_amend = self.amend_order(order)
            del single_amend["category"]
            batched_amends.append(order)

        format = {**self.base_payload, "request": batched_amends}

        return format

    def cancel_order(self, order):
        return {
            **self.base_payload,
            **({"orderId": order.orderId} if order.orderId else {}),
            **({"orderLinkId": order.clientOrderId} if order.clientOrderId else {}),
        }

    def batch_cancel_orders(self, orders: List[Order]) -> Dict:
        batched_cancels = []

        for order in orders:
            single_cancel = self.cancel_order(order)
            del single_cancel["category"]
            batched_cancels.append(order)

        format = {**self.base_payload, "request": batched_cancels}

        return format

    def cancel_all_orders(self, symbol):
        return {**self.base_payload, "symbol": symbol}

    def get_ohlcv(self, symbol, interval):
        return {
            **self.base_payload,
            "symbol": symbol,
            "interval": str(interval),
            "limit": "1000",  # NOTE: [1, 1000]. Default: 200
        }

    def get_trades(self, symbol):
        return {
            **self.base_payload,
            "symbol": symbol,
            "limit": "1000",  # NOTE: [1,1000], default: 500
        }

    def get_orderbook(self, symbol):
        return {
            **self.base_payload,
            "symbol": symbol,
            "limit": "200",  # NOTE: [1, 200]. Default: 25
        }

    def get_ticker(self, symbol):
        return {**self.base_payload, "symbol": symbol}

    def get_open_orders(self, symbol):
        return {**self.base_payload, "symbol": symbol, "limit": "50"}

    def get_position(self, symbol):
        return {**self.base_payload, "symbol": symbol}

    def get_account_info(self) -> Dict:
        return self.base_payload

    def get_instrument_info(self, symbol: str) -> Dict:
        return {**self.base_payload, "symbol": symbol}

    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        return {
            **self.base_payload,
            "symbol": symbol,
            "buyLeverage": leverage,
            "sellLeverage": leverage,
        }

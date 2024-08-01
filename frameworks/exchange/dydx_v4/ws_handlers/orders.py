from typing import List, Dict

from frameworks.exchange.base.constants import Order
from frameworks.exchange.base.ws_handlers.orders import OrdersHandler
from frameworks.exchange.dydx_v4.types import (
    DydxSideConverter,
    DydxOrderTypeConverter,
    DydxTimeInForceConverter,
)


class DydxOrdersHandler(OrdersHandler):
    _overwrite_ = set(("Created", "New", "PartiallyFilled"))
    _remove_ = set(("Rejected", "Filled", "Cancelled"))

    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["orders"])

        self.side_converter = DydxSideConverter()
        self.order_type_converter = DydxOrderTypeConverter()
        self.tif_converter = DydxTimeInForceConverter()

    def refresh(self, recv: Dict) -> None:
        try:
            for order in recv:
                if order["ticker"] != self.symbol:
                    continue

                new_order = Order(
                    symbol=self.symbol,
                    side=self.side_converter.to_num(order["side"]),
                    orderType=self.order_type_converter.to_num(order["type"]),
                    timeInForce=self.tif_converter.to_num(order["timeInForce"]),
                    price=float(order["price"]),
                    size=float(order["size"]) - float(order["totalFilled"]),
                    orderId=order["id"],
                    clientOrderId=order["clientId"],
                )

                self.orders[new_order.orderId] = new_order

        except Exception as e:
            raise Exception(f"Orders refresh - {e}")

    def process(self, recv: Dict) -> None:
        try:
            for order in recv["data"]:
                if order["symbol"] != self.symbol:
                    continue

                if order["orderStatus"] in self._overwrite_:
                    new_order = Order(
                        symbol=self.symbol,
                        side=self.side_converter.to_num(order["side"]),
                        orderType=self.order_type_converter.to_num(order["origType"]),
                        timeInForce=self.tif_converter.to_num(order["timeInForce"]),
                        price=float(order["price"]),
                        size=float(order["qty"]) - float(order["leavesQty"]),
                        orderId=order["orderId"],
                        clientOrderId=order["clientOrderId"],
                    )

                    self.orders[new_order.orderId] = new_order

                elif order["orderStatus"] in self._remove_:
                    del self.orders[order["orderId"]]

        except Exception as e:
            raise Exception(f"Orders process - {e}")

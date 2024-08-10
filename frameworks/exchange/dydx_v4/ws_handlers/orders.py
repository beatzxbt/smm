from typing import List, Dict, Any

from frameworks.exchange.base.ws_handlers.orders import Order, Orders, OrdersHandler
from frameworks.exchange.dydx_v4.types import (
    DydxSideConverter,
    DydxOrderTypeConverter,
    DydxTimeInForceConverter,
)


class DydxOrdersHandler(OrdersHandler):
    _overwrite_ = {"OPEN", "BEST_EFFORT_OPENED"}
    _remove_ = {"FILLED", "CANCELED", "BEST_EFFORT_CANCELED", "UNTRIGGERED"}

    def __init__(self, orders: Orders, symbol: str) -> None:
        super().__init__(orders)
        self.symbol = symbol

        self.side_converter = DydxSideConverter()
        self.order_type_converter = DydxOrderTypeConverter()
        self.tif_converter = DydxTimeInForceConverter()

    def refresh(self, recv: Dict[str, Any]) -> None:
        try:
            for order in recv:
                if order["ticker"] != self.symbol:
                    continue

                new_order = Order(
                    symbol=self.symbol,
                    side=self.side_converter.to_num(order.get("side")),
                    orderType=self.order_type_converter.to_num(order.get("type")),
                    timeInForce=self.tif_converter.to_num(order.get("timeInForce")),
                    price=float(order.get("price")),
                    size=float(order.get("size")) - float(order.get("totalFilled")),
                    orderId=order.get("id"),
                    clientOrderId=order.get("clientId"),
                )

                self.orders[new_order.orderId] = new_order

        except Exception as e:
            raise Exception(f"Orders refresh - {e}")

    def process(self, recv: Dict[str, Any]) -> None:
        try:
            for order in recv["data"]:
                if order["symbol"] != self.symbol:
                    continue

                if order["orderStatus"] in self._overwrite_:
                    new_order = Order(
                        symbol=self.symbol,
                        side=self.side_converter.to_num(order.get("side")),
                        orderType=self.order_type_converter.to_num(order.get("type")),
                        timeInForce=self.tif_converter.to_num(order.get("timeInForce")),
                        price=float(order.get("price")),
                        size=float(order.get("size")) - float(order.get("totalFilled")),
                        orderId=order.get("id"),
                        clientOrderId=order.get("clientId"),
                    )

                    self.orders[new_order.orderId] = new_order

                elif order["orderStatus"] in self._remove_:
                    del self.orders[order["orderId"]]

        except Exception as e:
            raise Exception(f"Orders process - {e}")

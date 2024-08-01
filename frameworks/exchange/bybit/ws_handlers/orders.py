from typing import List, Dict, Any

from frameworks.exchange.base.ws_handlers.orders import Order, Orders, OrdersHandler
from frameworks.exchange.bybit.types import (
    BybitSideConverter,
    BybitOrderTypeConverter,
    BybitTimeInForceConverter,
)


class BybitOrdersHandler(OrdersHandler):
    _overwrite_ = {"Created", "New", "PartiallyFilled"}
    _remove_ = {"Rejected", "Filled", "Cancelled"}

    def __init__(self, orders: Orders, symbol: str) -> None:
        super().__init__(orders)
        self.symbol = symbol

        self.side_converter = BybitSideConverter()
        self.order_type_converter = BybitOrderTypeConverter()
        self.tif_converter = BybitTimeInForceConverter()

    def refresh(self, recv: Dict[str, Any]) -> None:
        try:
            for order in recv["list"]:
                if order["symbol"] != self.symbol:
                    continue

                new_order = Order(
                    symbol=self.symbol,
                    side=self.side_converter.to_num(order.get("side")),
                    orderType=self.order_type_converter.to_num(order.get("origType")),
                    timeInForce=self.tif_converter.to_num(order.get("timeInForce")),
                    price=float(order.get("price")),
                    size=float(order.get("qty")) - float(order.get("leavesQty")),
                    orderId=order.get("orderId"),
                    clientOrderId=order.get("orderLinkId"),
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
                        orderType=self.order_type_converter.to_num(order.get("origType")),
                        timeInForce=self.tif_converter.to_num(order.get("timeInForce")),
                        price=float(order.get("price")),
                        size=float(order.get("qty")) - float(order.get("leavesQty")),
                        orderId=order.get("orderId"),
                        clientOrderId=order.get("orderLinkId"),
                    )

                    self.orders[new_order.orderId] = new_order

                elif order["orderStatus"] in self._remove_:
                    del self.orders[order.get("orderId")]

        except Exception as e:
            raise Exception(f"Orders process - {e}")

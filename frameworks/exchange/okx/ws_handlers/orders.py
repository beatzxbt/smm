from typing import Dict

from frameworks.exchange.base.types import Order
from frameworks.exchange.base.ws_handlers.orders import OrdersHandler
from frameworks.exchange.okx.types import (
    OkxSideConverter,
    OkxOrderTypeConverter,
    OkxTimeInForceConverter,
)


class OkxOrdersHandler(OrdersHandler):
    _overwrite_ = set(("live", "PartiallyFilled"))

    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["orders"])

        self.side_converter = OkxSideConverter
        self.order_type_converter = OkxOrderTypeConverter
        self.tif_converter = OkxTimeInForceConverter

    def refresh(self, recv: Dict) -> None:
        try:
            for order in recv["list"]:
                if order["symbol"] != self.symbol:
                    continue

                new_order = Order(
                    symbol=self.symbol,
                    side=self.side_converter.to_num(order["side"]),
                    # orderType=self.order_type_converter.to_num(order["ordType"]),
                    # timeInForce=self.tif_converter.to_num(order["ordType"]),
                    price=float(order["px"]),
                    size=float(order["sz"]),
                    orderId=order["ordId"],
                    clientOrderId=order["clOrdId"],
                )

                self.orders[new_order.orderId] = new_order

        except Exception as e:
            raise Exception(f"[Orders refresh] {e}")

    def process(self, recv: Dict) -> None:
        try:
            for order in recv["data"]:
                if order["symbol"] != self.symbol:
                    continue

                if order["orderStatus"] in self._overwrite_:
                    new_order = Order(
                        symbol=self.symbol,
                        side=self.side_converter.to_num(order["side"]),
                        # orderType=self.order_type_converter.to_num(order["ordType"]),
                        timeInForce=self.tif_converter.to_num(order["ordType"]),
                        price=float(order["px"]),
                        size=float(order["sz"]),
                        orderId=order["ordId"],
                        clientOrderId=order["clOrdId"],
                    )

                    self.orders[new_order.orderId] = new_order

                else:
                    del self.orders[order["ordId"]]

        except Exception as e:
            raise Exception(f"[Orders process] {e}")

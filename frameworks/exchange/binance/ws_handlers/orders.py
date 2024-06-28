from typing import List, Dict
from frameworks.exchange.base.ws_handlers.orders import OrdersHandler
from frameworks.exchange.binance.types import BinanceSideConverter, BinanceOrderTypeConverter, BinanceTimeInForceConverter

from frameworks.exchange.base.types import Order


class BinanceOrdersHandler(OrdersHandler):
    _overwrite_ = set(("NEW", "PARTIALLY_FILLED"))
    _remove_ = set(("CANCELLED", "EXPIRED", "FILLED", "EXPIRED_IN_MATCH"))

    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["orders"])

        self.side_converter = BinanceSideConverter
        self.order_type_converter = BinanceOrderTypeConverter
        self.tif_converter = BinanceTimeInForceConverter

    def refresh(self, recv: List[Dict]) -> None:
        try:
            for order in recv:
                if order["symbol"] != self.symbol:
                    continue
                
                new_order = Order(
                    symbol=self.symbol,
                    side=self.side_converter.to_num(order["side"]),
                    orderType=self.order_type_converter.to_num(order["origType"]),
                    timeInForce=self.tif_converter.to_num(order["timeInForce"]),
                    price=float(order["price"]),
                    size=float(order["origQty"]) - float(order["executedQty"]),
                    orderId=order["orderId"],
                    clientOrderId=order["clientOrderId"]
                )

                self.orders[new_order.orderId] = new_order

        except Exception as e:
            raise Exception(f"[Orders refresh] {e}")

    def process(self, recv: Dict) -> None:
        try:
            order = recv["o"]
            if order["s"] != self.symbol:
                return

            if order["X"] in self._overwrite_:
                new_order = Order(
                    symbol=self.symbol,
                    side=self.side_converter.to_num(order["S"]),
                    orderType=self.order_type_converter.to_num(order["o"]),
                    timeInForce=self.tif_converter.to_num(order["f"]),
                    price=float(order["p"]),
                    size=float(order["q"]) - float(order["z"]),
                    orderId=order["i"],
                    clientOrderId=order["c"]
                )

                self.orders[new_order.orderId] = new_order

            elif order["X"] in self._remove_:
                del self.orders[order["i"]]

        except Exception as e:
            raise Exception(f"[Orders process] {e}")

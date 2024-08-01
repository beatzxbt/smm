from typing import List, Dict

from frameworks.exchange.base.ws_handlers.orders import Order, Orders, OrdersHandler
from frameworks.exchange.binance.types import (
    BinanceSideConverter, 
    BinanceOrderTypeConverter, 
    BinanceTimeInForceConverter
)

class BinanceOrdersHandler(OrdersHandler):
    _overwrite_ = {"NEW", "PARTIALLY_FILLED"}
    _remove_ = {"CANCELLED", "EXPIRED", "FILLED", "EXPIRED_IN_MATCH"}

    def __init__(self, orders: Orders, symbol: str) -> None:
        super().__init__(orders)
        self.symbol = symbol

        self.side_converter = BinanceSideConverter()
        self.order_type_converter = BinanceOrderTypeConverter()
        self.tif_converter = BinanceTimeInForceConverter()

    def refresh(self, recv: List[Dict]) -> None:
        try:
            for order in recv:
                if order["symbol"] != self.symbol:
                    continue
                
                new_order = Order(
                    symbol=self.symbol,
                    side=self.side_converter.to_num(order.get("side")),
                    orderType=self.order_type_converter.to_num(order.get("origType")),
                    timeInForce=self.tif_converter.to_num(order.get("timeInForce")),
                    price=float(order.get("price")),
                    size=float(order.get("origQty")) - float(order.get("executedQty")),
                    orderId=order.get("orderId"),
                    clientOrderId=order.get("clientOrderId")
                )

                self.orders[new_order.orderId] = new_order

        except Exception as e:
            raise Exception(f"Orders refresh - {e}")

    def process(self, recv: Dict) -> None:
        try:
            order: Dict = recv["o"]
 
            if order["s"] != self.symbol:
                return None

            if order["X"] in self._overwrite_:
                new_order = Order(
                    symbol=self.symbol,
                    side=self.side_converter.to_num(order.get("S")),
                    orderType=self.order_type_converter.to_num(order.get("o")),
                    timeInForce=self.tif_converter.to_num(order.get("f")),
                    price=float(order.get("p")),
                    size=float(order.get("q")) - float(order.get("z")),
                    orderId=order.get("i"),
                    clientOrderId=order.get("c")
                )

                self.orders[new_order.orderId] = new_order

            elif order["X"] in self._remove_:
                del self.orders[order.get("i")]

        except Exception as e:
            raise Exception(f"Orders process - {e}")

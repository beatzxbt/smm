from typing import List, Dict
from frameworks.exchange.base.ws_handlers.orders import OrdersHandler
from frameworks.exchange.binance.types import BinanceOrderSides, BinanceOrderTypes


class BinanceOrdersHandler(OrdersHandler):
    _overwrite_ = set(("NEW", "PARTIALLY_FILLED"))
    _remove_ = set(("CANCELLED", "EXPIRED", "FILLED", "EXPIRED_IN_MATCH"))

    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["orders"])

    def refresh(self, recv: List[Dict]) -> None:
        try:
            for order in recv:
                if order["symbol"] != self.symbol:
                    continue

                self.format["createTime"] = float(order["time"])
                self.format["side"] = BinanceOrderSides.to_num(order["side"])
                self.format["price"] = float(order["price"])
                self.format["size"] = float(order["origQty"]) - float(
                    order["executedQty"]
                )
                self.orders[order["orderId"]] = self.format.copy()

        except Exception as e:
            raise Exception(f"Orders Refresh :: {e}")

    def process(self, recv: Dict) -> None:
        try:
            order = recv["o"]
            if order["s"] != self.symbol:
                return

            if order["X"] in self._overwrite_:
                self.format["createTime"] = float(order["T"])
                self.format["side"] = BinanceOrderSides.to_num(order["S"])
                self.format["price"] = float(order["p"])
                self.format["size"] = float(order["q"]) - float(order["z"])
                self.orders[order["i"]] = self.format.copy()

            elif order["X"] in self._remove_:
                del self.orders[order["i"]]

        except Exception as e:
            raise Exception(f"Orders Process :: {e}")

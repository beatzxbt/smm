from typing import List, Dict

from frameworks.exchange.base.ws_handlers.orders import OrdersHandler
from frameworks.exchange.dydx_v4.types import DydxOrderTypeConverter, DydxSideConverter


class DydxOrdersHandler(OrdersHandler):
    _overwrite_ = set(("Created", "New", "PartiallyFilled"))
    _remove_ = set(("Rejected", "Filled", "Cancelled"))

    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["orders"])

    def refresh(self, recv: Dict) -> None:
        try:
            for order in recv["list"]:
                if order["symbol"] != self.symbol:
                    continue

                self.format["createTime"] = float(order["time"])
                self.format["side"] = DydxSideConverter.to_num(order["side"])
                self.format["price"] = float(order["price"])
                self.format["size"] = float(order["qty"]) - float(order["leavesQty"])
                self.orders[order["orderId"]] = self.format.copy()

        except Exception as e:
            raise Exception(f"Orders Refresh :: {e}")

    def process(self, recv: Dict) -> None:
        try:
            for order in recv["contents"]["orders"]:
                if order["ticker"] != self.symbol:
                    continue

                if order["status"] in self._overwrite_:
                    self.format["createTime"] = float(order["updatedAt"])
                    self.format["side"] = DydxSideConverter.to_num(order["side"])
                    self.format["price"] = float(order["price"])
                    self.format["size"] = float(order["size"]) - float(
                        order["totalFilled"]
                    )
                    self.format["orderId"] = order["id"]
                    self.format["clientOrderId"] = order["clientId"]
                    self.orders[order["id"]] = self.format.copy()

                elif order["status"] in self._remove_:
                    del self.orders[order["id"]]

        except Exception as e:
            raise Exception(f"Orders Process :: {e}")

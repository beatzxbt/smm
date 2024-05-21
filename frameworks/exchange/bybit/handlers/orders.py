from typing import List, Dict
from frameworks.exchange.base.ws_handlers.orders import OrdersHandler

from frameworks.exchange.bybit.types import BybitOrderSides, BybitOrderTypes

class BybitOrdersHandler(OrdersHandler):
    _overwrite_ = set(("Created", "New", "PartiallyFilled"))
    _remove_ = set(("Rejected", "Filled", "Cancelled"))

    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["orders"])
    
    def refresh(self, recv: Dict) -> None:
        try:
            for order in recv["list"]:
                if order["symbol"] != self.ss.symbol:
                    continue

                self.format["createTime"] = float(order["time"])
                self.format["side"] = BybitOrderSides.to_num(order["side"])
                self.format["price"] = float(order["price"])
                self.format["size"] = float(order["qty"]) - float(order["leavesQty"])
                self.orders[order["orderId"]] = self.format.copy()

        except Exception as e:
            raise Exception(f"Orders Refresh :: {e}")

    def process(self, recv: Dict) -> None:
        try:
            for order in recv["data"]:
                if order["symbol"] != self.ss.symbol:
                    continue

                if order["orderStatus"] in self._overwrite_:
                    self.format["createTime"] = float(order["createdTime"])
                    self.format["side"] = BybitOrderSides.to_num(order["side"])
                    self.format["price"] = float(order["price"])
                    self.format["size"] = float(["qty"]) - float(order["leavesQty"])
                    self.orders[order["orderId"]] = self.format.copy()

                elif order["orderStatus"] in self._remove_:
                    del self.orders[order["orderId"]]

        except Exception as e:
            raise Exception(f"Orders Process :: {e}")
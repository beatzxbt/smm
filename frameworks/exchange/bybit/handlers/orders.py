from typing import List, Dict
from frameworks.exchange.base.ws_handlers.orders import OrdersHandler

from frameworks.exchange.bybit.types import BybitOrderSides, BybitOrderTypes
from frameworks.sharedstate import SharedState

class BybitOrdersHandler(OrdersHandler):
    _overwrite_ = set(("Created", "New", "PartiallyFilled"))
    _remove_ = set(("Rejected", "Filled", "Cancelled"))

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.current_orders)
    
    def sync(self, recv: Dict) -> None:
        for order in recv["list"]:
            if order["symbol"] != self.ss.symbol:
                continue

            self.single_order["createTime"] = float(order["time"])
            self.single_order["side"] = BybitOrderSides.to_int(order["side"])
            self.single_order["price"] = float(order["price"])
            self.single_order["size"] = float(order["qty"]) - float(order["leavesQty"])
            self.current_orders[order["orderId"]] = self.single_order.copy()

    def process(self, recv: Dict) -> None:
        for order in recv["data"]:
            if order["symbol"] != self.ss.symbol:
                continue

            if order["orderStatus"] in self._overwrite_:
                self.single_order["createTime"] = float(order["createdTime"])
                self.single_order["side"] = BybitOrderSides.to_int(order["side"])
                self.single_order["price"] = float(order["price"])
                self.single_order["size"] = float(["qty"]) - float(order["leavesQty"])
                self.current_orders[order["orderId"]] = self.single_order.copy()

            elif order["orderStatus"] in self._remove_:
                del self.current_orders[order["orderId"]]
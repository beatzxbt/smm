from typing import List, Dict
from frameworks.exchange.base.ws_handlers.orders import OrdersHandler

from frameworks.exchange.hyperliquid.types import HyperliquidOrderSides, HyperliquidOrderTypes
from frameworks.sharedstate import SharedState

class HyperliquidOrdersHandler(OrdersHandler):
    _overwrite_ = set(("open"))
    _remove_ = set(("filled", "canceled", "triggered", "rejected", "marginCanceled"))

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.current_orders)

        self.asset_idx = 0
        self.asset_found = False
    
    def refresh(self, recv: List) -> None:
        for order in recv:
            if order["coin"] != self.ss.symbol:
                continue

            self.single_order["createTime"] = float(recv["order"]["timestamp"])
            self.single_order["side"] = HyperliquidOrderSides.to_int(recv["order"]["side"])
            self.single_order["price"] = float(recv["order"]["limitPx"])
            self.single_order["size"] = float(["sz"])
            self.current_orders[recv["order"]["oid"]] = self.single_order.copy()

    def process(self, recv: Dict) -> None:
        for order in recv["orderHistory"]:
            if order["coin"] != self.ss.symbol:
                continue

            if recv["status"] in self._overwrite_:
                self.single_order["createTime"] = float(order["timestamp"])
                self.single_order["side"] = HyperliquidOrderSides.to_int(order["side"])
                self.single_order["price"] = float(order["limitPx"])
                self.single_order["size"] = float(["sz"])
                self.current_orders[order["oid"]] = self.single_order.copy()

            elif recv["status"] in self._remove_:
                del self.current_orders[order["oid"]]
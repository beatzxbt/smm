from typing import List, Dict
from frameworks.exchange.base.ws_handlers.orders import OrdersHandler
from frameworks.exchange.binance.types import BinanceOrderSides, BinanceOrderTypes
from frameworks.sharedstate import SharedState

class BinanceOrdersHandler(OrdersHandler):
    _overwrite_ = set(("NEW", "PARTIALLY_FILLED"))
    _remove_ = set(("CANCELLED", "EXPIRED", "FILLED", "EXPIRED_IN_MATCH"))

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.current_orders)
    
    def sync(self, recv: List[Dict]) -> None:
        for order in recv:
            self.single_order["createTime"] = float(order["time"])
            self.single_order["side"] = BinanceOrderSides.to_int(order["side"])
            self.single_order["price"] = float(order["price"])
            self.single_order["size"] = float(order["origQty"]) - float(order["executedQty"])
            self.current_orders[order["orderId"]] = self.single_order.copy()

    def process(self, recv: Dict) -> None:
        if recv["o"]["X"] in self._overwrite_:
            self.single_order["createTime"] = float(recv["o"]["T"])
            self.single_order["side"] = BinanceOrderSides.to_int(recv["o"]["S"])
            self.single_order["price"] = float(recv["o"]["i"])
            self.single_order["size"] = float(recv["o"]["q"]) - float(recv["o"]["z"])
            self.current_orders[recv["o"]["c"]] = self.single_order.copy()

        elif recv["o"]["X"] in self._remove_:
            del self.current_orders[recv["o"]["c"]]
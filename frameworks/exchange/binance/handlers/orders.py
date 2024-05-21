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
        for order in recv:
            self.format["createTime"] = float(order["time"])
            self.format["side"] = BinanceOrderSides.to_num(order["side"])
            self.format["price"] = float(order["price"])
            self.format["size"] = float(order["origQty"]) - float(order["executedQty"])
            self.orders[order["orderId"]] = self.format.copy()

    def process(self, recv: Dict) -> None:
        if recv["o"]["s"] != self.symbol:
            return None

        if recv["o"]["X"] in self._overwrite_:
            self.format["createTime"] = float(recv["o"]["T"])
            self.format["side"] = BinanceOrderSides.to_num(recv["o"]["S"])
            self.format["price"] = float(recv["o"]["i"])
            self.format["size"] = float(recv["o"]["q"]) - float(recv["o"]["z"])
            self.orders[recv["o"]["c"]] = self.format.copy()

        elif recv["o"]["X"] in self._remove_:
            del self.orders[recv["o"]["c"]]

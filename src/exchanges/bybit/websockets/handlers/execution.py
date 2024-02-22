from typing import List
from src.sharedstate import SharedState


class BybitExecutionHandler:
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.symbol = self.ss.bybit_symbol

    def process(self, data: List) -> None:
        for execution in data:
            if execution["symbol"] != self.symbol:
                continue

            self.ss.execution_feed.append({
                execution["orderId"]: {
                    "side": execution["side"],
                    "price": float(execution["execPrice"]),
                    "qty": float(execution["execQty"]),
                }
            })
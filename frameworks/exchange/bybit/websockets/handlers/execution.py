
from frameworks.sharedstate.private import PrivateDataSharedState


class BybitExecutionHandler:


    def __init__(self, sharedstate: PrivateDataSharedState, symbol: str) -> None:
        self.pdss = sharedstate
        self.symbol = symbol
        self.bybit = self.pdss.bybit["Data"][self.symbol]


    def update(self, data: list) -> None:
        for execution in data:
            if execution["symbol"] == self.symbol:
                self.bybit["execution_feed"].append({
                    execution["orderId"]: {
                        "side": execution["side"],
                        "price": float(execution["execPrice"]),
                        "qty": float(execution["execQty"]),
                    }})
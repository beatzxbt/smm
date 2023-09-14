
from src.sharedstate import SharedState


class BybitExecutionHandler:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.symbol = self.ss.bybit_symbol


    def process(self, data):

        for execution in data:

            if execution["symbol"] == self.symbol:
                
                self.ss.execution_feed.append({
                    execution["orderId"]: {
                        "side": execution["side"],
                        "price": float(execution["execPrice"]),
                        "qty": float(execution["execQty"]),
                    }})
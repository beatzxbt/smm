from typing import Dict

from frameworks.exchange.base.ws_handlers.trades import TradesHandler
from frameworks.sharedstate import SharedState


class BybitTradesHandler(TradesHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.trades)
    
    def refresh(self, recv: Dict) -> None:
        for trade in recv["list"]:
            self.format[0] = float(trade["time"])
            self.format[1] = 0.0 if trade["side"] == "Buy" else 1.0
            self.format[2] = float(trade["price"])
            self.format[3] = float(trade["size"])
            self.trades.append(self.format.copy())
    
    def process(self, recv: Dict) -> None:
        self.format[0] = float(recv["data"]["T"])
        self.format[1] = 0.0 if recv["data"]["S"] == "Buy" else 1.0
        self.format[2] = float(recv["data"]["p"])
        self.format[3] = float(recv["data"]["v"])
        self.trades.append(self.format.copy())
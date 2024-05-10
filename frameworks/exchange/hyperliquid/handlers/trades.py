from typing import List, Dict

from frameworks.exchange.base.ws_handlers.trades import TradesHandler
from frameworks.exchange.hyperliquid.types import HyperliquidOrderSides
from frameworks.sharedstate import SharedState


class HyperliquidTradesHandler(TradesHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.trades)
    
    def refresh(self, recv: List[Dict]) -> None:
        for trade in recv:
            self.format[0] = float(trade["time"])
            self.format[1] = HyperliquidOrderSides.to_int(trade["side"])
            self.format[2] = float(trade["px"])
            self.format[3] = float(trade["sz"])
            self.trades.append(self.format.copy())
    
    def process(self, recv: Dict) -> None:
        for trade in recv["data"]:
            self.format[0] = float(trade["time"])
            self.format[1] = HyperliquidOrderSides.to_int(trade["side"])
            self.format[2] = float(trade["px"])
            self.format[3] = float(trade["sz"])
            self.trades.append(self.format.copy())
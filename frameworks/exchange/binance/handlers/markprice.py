from typing import Dict
from frameworks.exchange.base.ws_handlers.ticker import TickerHandler
from frameworks.sharedstate import SharedState

class BinanceTickerHandler(TickerHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.ticker)
        
    def process(self, recv: Dict) -> None:
        self.format["markPrice"] = float(recv["p"])
        self.format["indexPrice"] = float(recv["i"])
        self.format["fundingTime"] = float(recv["T"])
        self.format["fundingRate"] = float(recv["r"])
        self.ticker.update(self.format)
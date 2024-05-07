from typing import Dict

from frameworks.exchange.base.ws_handlers.ticker import TickerHandler
from frameworks.sharedstate import SharedState

class BybitTickerHandler(TickerHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.ticker)
    
    def refresh(self, recv: Dict) -> None:
        pass
    
    def process(self, recv: Dict) -> None:
        self.format["markPrice"] = float(recv["data"]["markPrice"])
        self.format["indexPrice"] = float(recv["data"]["indexPrice"])
        self.format["fundingRate"] = float(recv["data"]["fundingRate"])
        self.format["fundingTime"] = float(recv["data"]["nextFundingTime"])
        self.ticker.update(self.format)
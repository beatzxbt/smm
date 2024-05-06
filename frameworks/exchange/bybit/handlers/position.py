from typing import List, Dict

from frameworks.exchange.base.ws_handlers.position import PositionHandler
from frameworks.sharedstate import SharedState

class BybitPositionHandler(PositionHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.current_position)
    
    def sync(self, recv: Dict) -> None:
        for position in recv["list"]:
            if position["symbol"] != self.ss.symbol:
                continue

            self.position["price"] = float(position["avgPrice"])
            self.position["size"] = float(position["size"])
            self.position["uPnL"] = float(position["unrealisedPnl"])
            self.current_position.update(self.position)

    def process(self, recv: Dict) -> None:
        for position in recv["data"]:
            if position["symbol"] != self.ss.symbol:
                continue

            self.position["price"] = float(position["entryPrice"])
            self.position["size"] = float(position["size"])
            self.position["uPnL"] = float(position["unrealizedPnl"])
            self.current_position.update(self.position)
from typing import List, Dict
from frameworks.exchange.base.ws_handlers.position import PositionHandler
from frameworks.sharedstate import SharedState

class BinancePositionHandler(PositionHandler):
    _event_reason_ = "ORDER"

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.current_position)
    
    def sync(self, recv: List[Dict]) -> None:
        for position in recv:
            if position["symbol"] != self.ss.symbol:
                continue

            self.position["price"] = float(position["entryPrice"])
            self.position["size"] = float(position["positionAmt"])
            self.position["uPnL"] = float(position["unRealizedProfit"])
            self.current_position.update(self.position)

    def process(self, recv: Dict) -> None:
        if recv["a"]["M"] == self._event_reason_:
            for position in recv["a"]["P"]:
                if position["s"] != self.ss.symbol:
                    continue

                self.position["price"] = float(position["ep"])
                self.position["size"] = float(position["pa"])
                self.position["uPnL"] = float(position["up"])
                self.current_position.update(self.position)

            for balance in recv["a"]["B"]:
                if balance["s"] != "USDT":
                    continue

                self.ss.account_balance = float(balance["wb"])
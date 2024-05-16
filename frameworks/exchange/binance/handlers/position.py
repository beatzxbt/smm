from typing import List, Dict

from frameworks.exchange.base.ws_handlers.position import PositionHandler


class BinancePositionHandler(PositionHandler):
    _event_reason_ = "ORDER"

    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["position"])

    def refresh(self, recv: List[Dict]) -> None:
        for position in recv:
            if position["symbol"] != self.symbol:
                continue

            self.format["price"] = float(position["entryPrice"])
            self.format["size"] = float(position["positionAmt"])
            self.format["uPnL"] = float(position["unRealizedProfit"])
            self.position.update(self.format)

    def process(self, recv: Dict) -> None:
        if recv["a"]["M"] == self._event_reason_:
            for position in recv["a"]["P"]:
                if position["s"] != self.symbol:
                    continue

                self.format["price"] = float(position["ep"])
                self.format["size"] = float(position["pa"])
                self.format["uPnL"] = float(position["up"])
                self.position.update(self.format)

            for balance in recv["a"]["B"]:
                if balance["s"] != "USDT":
                    continue

                self.data["account_balance"] = float(balance["wb"])

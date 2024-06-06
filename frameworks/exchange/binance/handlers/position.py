from typing import List, Dict

from frameworks.exchange.base.ws_handlers.position import PositionHandler


class BinancePositionHandler(PositionHandler):
    _event_reason_ = "ORDER"

    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["position"])

    def refresh(self, recv: List[Dict]) -> None:
        try:
            for position in recv:
                if position["symbol"] != self.symbol:
                    continue

                self.format["price"] = float(position["entryPrice"])
                self.format["size"] = float(position["positionAmt"])
                self.format["uPnL"] = float(position["unRealizedProfit"])
                self.position.update(self.format)
        except Exception as e:
            raise Exception(f"Position Refresh :: {e}")

    def process(self, recv: Dict) -> None:
        try:
            if recv["a"]["m"] == self._event_reason_:
                for position in recv["a"]["P"]:
                    if position["s"] != self.symbol:
                        continue

                    self.format["price"] = float(position["ep"])
                    self.format["size"] = float(position["pa"])
                    self.format["uPnL"] = float(position["up"])
                    self.position.update(self.format)

                for balance in recv["a"]["B"]:
                    if balance["a"] != "USDT":
                        continue

                    self.data["account_balance"] = float(balance["wb"])
        except Exception as e:
            raise Exception(f"Position Process :: {e}")

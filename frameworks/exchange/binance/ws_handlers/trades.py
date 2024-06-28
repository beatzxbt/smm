from typing import List, Dict

from frameworks.exchange.base.types import Side
from frameworks.exchange.base.ws_handlers.trades import TradesHandler


class BinanceTradesHandler(TradesHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["trades"])

    def refresh(self, recv: List[Dict]) -> None:
        try:
            for trade in recv:
                self.format[0] = float(trade["time"])
                self.format[1] = Side.SELL if trade["isBuyerMaker"] else Side.BUY
                self.format[2] = float(trade["price"])
                self.format[3] = float(trade["qty"])
                self.trades.append(self.format.copy())

        except Exception as e:
            raise Exception(f"[Trades refresh] {e}")

    def process(self, recv: Dict) -> None:
        try:
            self.format[0] = float(recv["T"])
            self.format[1] = Side.SELL if recv["m"] else Side.BUY
            self.format[2] = float(recv["p"])
            self.format[3] = float(recv["q"])
            self.trades.append(self.format.copy())

        except Exception as e:
            raise Exception(f"[Trades process] {e}")

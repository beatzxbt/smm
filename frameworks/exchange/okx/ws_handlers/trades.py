from typing import List, Dict

from frameworks.exchange.base.ws_handlers.trades import TradesHandler
from frameworks.exchange.okx.types import OkxSideConverter


class OkxTradesHandler(TradesHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["trades"])

    def refresh(self, recv: Dict) -> None:
        try:
            for trade in recv["data"]:
                self.format[0] = float(trade["ts"])
                self.format[1] = OkxSideConverter.to_num(trade["side"])
                self.format[2] = float(trade["px"])
                self.format[3] = float(trade["sz"])
                self.trades.append(self.format.copy())

        except Exception as e:
            raise Exception(f"[Trades refresh] {e}")

    def process(self, recv: Dict) -> None:
        try:
            for trade in recv["data"]:
                self.format[0] = float(trade["ts"])
                self.format[1] = OkxSideConverter.to_num(trade["side"])
                self.format[2] = float(trade["px"])
                self.format[3] = float(trade["sz"])
                self.trades.append(self.format.copy())

        except Exception as e:
            raise Exception(f"[Trades process] {e}")

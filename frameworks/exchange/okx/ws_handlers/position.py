from typing import List, Dict

from frameworks.exchange.base.ws_handlers.position import PositionHandler
from frameworks.exchange.okx.types import OkxPositionDirectionConverter

class OkxPositionHandler(PositionHandler):
    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["position"])

        self.position_side_converter = OkxPositionDirectionConverter

    def refresh(self, recv: Dict) -> None:
        try:
            for position in recv["data"]:
                if position["instId"] != self.symbol:
                    continue

                self.position.update(
                    side=self.position_side_converter.to_num(position["posSide"]),
                    price=float(position["avgPx"]),
                    size=float(position["pos"]),
                    uPnl=float(position["upl"]),
                )

        except Exception as e:
            raise Exception(f"[Position refresh] {e}")

    def process(self, recv):
        try:
            for position in recv["data"]:
                if position["instId"] != self.symbol:
                    continue

                self.position.update(
                    side=self.position_side_converter.to_num(position["posSide"]),
                    price=float(position["avgPx"]),
                    size=float(position["pos"]),
                    uPnl=float(position["upl"]),
                )

        except Exception as e:
            raise Exception(f"[Position process] {e}")

from typing import List, Dict

from frameworks.exchange.base.types import Position
from frameworks.exchange.base.ws_handlers.position import PositionHandler
from frameworks.exchange.bybit.types import BybitPositionDirectionConverter


class BybitPositionHandler(PositionHandler):
    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["position"])

        self.position_side_converter = BybitPositionDirectionConverter

    def refresh(self, recv: Dict) -> None:
        try:
            for position in recv["list"]:
                if position["symbol"] != self.symbol:
                    continue

                new_position = Position(
                    symbol=self.symbol,
                    side=self.position_side_converter.to_num(position["side"]),
                    price=float(position["avgPrice"]),
                    size=float(position["size"]),
                    uPnl=float(position["unrealisedPnl"]),
                )

                self.position = new_position

        except Exception as e:
            raise Exception(f"[Position refresh] {e}")

    def process(self, recv):
        try:
            for position in recv["data"]:
                if position["symbol"] != self.symbol:
                    continue

                self.position.update(
                    side=self.position_side_converter.to_num(position["side"]),
                    price=float(position["entryPrice"]),
                    size=float(position["size"]),
                    uPnl=float(position["unrealisedPnl"]),
                )

                break

        except Exception as e:
            raise Exception(f"[Position process] {e}")

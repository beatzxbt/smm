from typing import List, Dict, Any

from frameworks.exchange.base.ws_handlers.position import Position, PositionHandler
from frameworks.exchange.bybit.types import BybitPositionDirectionConverter

 
class BybitPositionHandler(PositionHandler):
    def __init__(self, position: Position, symbol: str) -> None:
        super().__init__(position)
        self.symbol = symbol

        self.position_side_converter = BybitPositionDirectionConverter()

    def refresh(self, recv: Dict[str, Any]) -> None:
        try:
            for position in recv["list"]:
                if position["symbol"] != self.symbol:
                    continue

                self.position = Position(
                    symbol=self.symbol,
                    side=self.position_side_converter.to_num(position.get("side")),
                    price=float(position.get("avgPrice")),
                    size=float(position.get("size")),
                    uPnl=float(position.get("unrealisedPnl"))
                )

        except Exception as e:
            raise Exception(f"Position refresh - {e}")

    def process(self, recv: Dict[str, Any]):
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

        except Exception as e:
            raise Exception(f"Position process - {e}")

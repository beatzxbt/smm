from typing import List, Dict, Any

from frameworks.exchange.base.ws_handlers.position import Position, PositionHandler
from frameworks.exchange.dydx_v4.types import DydxPositionDirectionConverter


class DydxPositionHandler(PositionHandler):
    def __init__(self, position: Position, symbol: str) -> None:
        super().__init__(position)
        self.symbol = symbol

        self.position_side_converter = DydxPositionDirectionConverter()

    def refresh(self, recv: Dict[str, Any]) -> None:
        try:
            for position in recv["positions"]:
                if position["symbol"] != self.symbol:
                    continue
                
                self.position.update(
                    symbol=self.symbol,
                    side=self.position_side_converter.to_num(position["side"]),
                    price=float(position["avgPrice"]),
                    size=float(position["size"]),
                    uPnl=float(position["unrealisedPnl"])
                )

        except Exception as e:
            raise Exception(f"Position refresh - {e}")

    def process(self, recv: Dict[str, Any]):
        try:
            for position in recv["contents"]:
                if position["market"] != self.symbol:
                    continue
                
                self.position.update(
                    side=self.position_side_converter.to_num(position["side"]),
                    price=float(position["entryPrice"]),
                    size=float(position["size"]),
                    uPnl=float(position["unrealisedPnl"])
                )

        except Exception as e:
            raise Exception(f"Position process - {e}")

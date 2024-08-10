from typing import List, Dict, Any

from frameworks.exchange.base.constants import PositionDirection
from frameworks.exchange.base.ws_handlers.position import Position, PositionHandler


class HyperliquidPositionHandler(PositionHandler):
    def __init__(self, position: Position, symbol: str) -> None:
        super().__init__(position)
        self.symbol = symbol
    
    def refresh(self, recv: List[Dict]) -> None:
        try:
            for position in recv["assetPositions"]:
                if position["coin"] != self.symbol:
                    continue

                self.position = Position(
                    symbol=self.symbol,
                    side=PositionDirection.LONG if float(position.get("szi")) >= 0 else PositionDirection.SHORT,
                    price=float(position.get("entryPx")),
                    size=float(position.get("szi")),
                    uPnl=float(position.get("unrealizedPnl"))
                )

        except Exception as e:
            raise Exception(f"Position refresh - {e}")

    def process(self, recv: Dict) -> None:
        try:
            for position in recv["assetPositions"]:
                if position["coin"] != self.symbol:
                    continue

                self.position = Position(
                    symbol=self.symbol,
                    side=PositionDirection.LONG if float(position.get("szi")) >= 0 else PositionDirection.SHORT,
                    price=float(position.get("entryPx")),
                    size=float(position.get("szi")),
                    uPnl=float(position.get("unrealizedPnl"))
                )

        except Exception as e:
            raise Exception(f"Position refresh - {e}")
from typing import List, Dict

from frameworks.exchange.base.ws_handlers.position import Position, PositionHandler
from frameworks.exchange.binance.types import BinancePositionDirectionConverter


class BinancePositionHandler(PositionHandler):
    _event_reason_ = "ORDER"

    def __init__(self, position: Position, symbol: str) -> None:
        super().__init__(position)
        self.symbol = symbol

        self.position_side_converter = BinancePositionDirectionConverter()

    def refresh(self, recv: List[Dict]) -> None:
        try:
            for position in recv:
                if position["symbol"] != self.symbol:
                    continue
                
                self.position = Position(
                    symbol=self.symbol,
                    side=self.position_side_converter.to_num(position.get("side")),
                    price=float(position.get("entryPrice")),
                    size=float(position.get("positionAmt")),
                    uPnl=float(position.get("unRealizedProfit"))
                )

        except Exception as e:
            raise Exception(f"Position refresh - {e}")

    def process(self, recv: Dict) -> None:
        try:
            if recv["a"]["m"] == self._event_reason_:
                for position in recv["a"]["P"]:
                    if position["s"] != self.symbol:
                        continue

                    self.position.update(
                        side=self.position_side_converter.to_num(position.get("ps")),
                        price=float(position.get("ep")),
                        size=float(position.get("pa")),
                        uPnl=float(position.get("up"))
                    )

        except Exception as e:
            raise Exception(f"Position process - {e}")

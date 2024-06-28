from typing import List, Dict

from frameworks.exchange.base.types import Position
from frameworks.exchange.base.ws_handlers.position import PositionHandler
from frameworks.exchange.binance.types import BinancePositionDirectionConverter


class BinancePositionHandler(PositionHandler):
    _event_reason_ = "ORDER"

    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["position"])

        self.position_side_converter = BinancePositionDirectionConverter

    def refresh(self, recv: List[Dict]) -> None:
        try:
            for position in recv:
                if position["symbol"] != self.symbol:
                    continue
                
                new_position = Position(
                    symbol=self.symbol,
                    side=self.position_side_converter.to_num(position["side"]),
                    price=float(position["entryPrice"]),
                    size=float(position["positionAmt"]),
                    uPnl=float(position["unRealizedProfit"])
                )

                self.position = new_position

        except Exception as e:
            raise Exception(f"[Position refresh] {e}")

    def process(self, recv: Dict) -> None:
        try:
            if recv["a"]["m"] == self._event_reason_:
                for position in recv["a"]["P"]:
                    if position["s"] != self.symbol:
                        continue

                    self.position.update(
                        side=self.position_side_converter.to_num(position["ps"]),
                        price=float(position["ep"]),
                        size=float(position["pa"]),
                        uPnl=float(position["up"])
                    )

                    break

                for balance in recv["a"]["B"]:
                    if balance["a"] != "USDT":
                        continue

                    self.data["account_balance"] = float(balance["wb"])

                    break

        except Exception as e:
            raise Exception(f"[Position process] {e}")

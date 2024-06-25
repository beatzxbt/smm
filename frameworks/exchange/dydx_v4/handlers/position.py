from typing import List, Dict

from frameworks.exchange.base.ws_handlers.position import PositionHandler
from frameworks.exchange.dydx_v4.types import DydxOrderTypeConverter


class DydxPositionHandler(PositionHandler):
    def __init__(self, data: Dict, symbol: str) -> None:
        self.data = data
        self.symbol = symbol
        super().__init__(self.data["position"])

    def refresh(self, recv: Dict) -> None:
        try:
            for position in recv["positions"]:
                if position["symbol"] != self.symbol:
                    continue
                
                self.format["createTime"] = 0 # NOTE: Field not available!
                self.format["price"] = float(position["avgPrice"])
                self.format["size"] = float(position["size"])
                self.format["uPnl"] = float(position["unrealisedPnl"])
                self.position.update(self.format)

        except Exception as e:
            raise Exception(f"Position Refresh :: {e}")

    def process(self, recv):
        try:
            for position in recv["contents"]:
                if position["market"] != self.symbol:
                    continue
                
                self.format["createTime"] = 0 # NOTE: Field not available!
                self.format["price"] = float(position["entryPrice"])
                self.format["size"] = -float(position["size"]) if position["side"] == "SHORT" else float(position["size"])
                self.format["uPnl"] = float(position["unrealisedPnl"])
                self.position.update(self.format)

        except Exception as e:
            raise Exception(f"Position Process :: {e}")

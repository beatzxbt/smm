from typing import Dict

class BinancePositionHandler:
    def __init__(self, private: Dict) -> None:
        self.private = private

    def process(self, recv: Dict) -> Dict:
        E = float(recv["E"])
        ts = float(recv["T"])

        # Prevent exchange pushing stale data
        if E >= ts: 
            if recv["a"]["M"] == "ORDER":
                for position in recv["a"]["P"]:
                    self.private[position["s"]]["currentPosition"] = {
                        "price": float(position["ep"]),
                        "qty": float(position["pa"]),
                        "uPnl": float(position["up"])
                    }

                for balance in recv["a"]["B"]:
                    if balance["s"] != "USDT":
                        continue
                    self.private["currentBalance"] = float(balance["wb"])

        else:
            # TODO: Figure out a way to trigger re-sync's in these cases
            pass

from typing import List, Dict
from frameworks.exchange.base.ws_handlers.position import PositionHandler
from frameworks.exchange.binance.types import BinanceOrderSides, BinanceOrderTypes
from frameworks.sharedstate import SharedState

class BinancePositionHandler(PositionHandler):
    _event_reason_ = "ORDER"

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.current_position)
    
    def sync(self, recv: List[Dict]) -> None:
        for order in recv:
            self.position["price"] = float(recv["o"]["i"])
            self.position["size"] = float(recv["o"]["q"]) - float(recv["o"]["z"])
            self.position["uPnL"] = float(recv["o"]["q"]) - float(recv["o"]["z"])
            self.current_position.update(self.position)

    def process(self, recv: Dict) -> None:
        if recv["a"]["M"] == self._event_reason_:
            self.position["price"] = float(position["ep"])
            self.position["size"] = float(position["pa"])
            self.position["uPnL"] = float(recv["o"]["q"]) - float(recv["o"]["z"])
            self.current_position.update(self.position)

    self.position = {
        "price": 0,
        "size": 0,
        "uPnL": 0
    }

        
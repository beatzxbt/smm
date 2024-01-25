from typing import Dict

class BinanceOrdersHandler:
    def __init__(self, private: Dict) -> None:
        self.private = private
        self._overwrite_ = ["NEW", "PARTIALLY_FILLED"]
        self._remove_ = ["CANCELLED", "EXPIRED", "FILLED", "EXPIRED_IN_MATCH"]

    def process(self, recv: Dict) -> Dict:
        E = float(recv["E"])
        ts = float(recv["k"]["t"])

        # Prevent exchange pushing stale data
        if E >= ts: 
            if recv["o"]["X"] in self._overwrite_:
                self.private[recv["o"]["s"]]["openOrders"][recv["o"]["i"]] = {
                    "time": float(recv["o"]["T"]),
                    "side": 1.0 if recv["o"]["S"] == "SELL" else 0.0,
                    "price": float(recv["o"]["i"]),
                    # "tp": None, NOTE: Add later...
                    "qty": float(recv["o"]["q"]),
                    "qtyRemaining": float(recv["o"]["q"]) - float(recv["o"]["z"]),
                }

            elif recv["o"]["X"] in self._remove_:
                del self.private[recv["o"]["s"]]["openOrders"][recv["o"]["i"]]

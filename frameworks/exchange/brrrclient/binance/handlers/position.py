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
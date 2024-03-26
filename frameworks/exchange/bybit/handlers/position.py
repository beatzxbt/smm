from typing import Dict

class BybitPositionHandler:
    def __init__(self, private: Dict) -> None:
        self.private = private
        self.position_pointer = None

    def process(self, recv: Dict) -> Dict:
        E = float(recv["ts"])
        ts = float(recv["data"][0]["start"])

        if self.position_pointer is None:
            self.position_pointer = self.private[recv["data"][0]["symbol"]]["currentPosition"]

        # Prevent exchange pushing stale data
        if E >= ts: 
            self.position_pointer["side"] = 0.0 if recv["data"][0]["side"] == "Buy" else 1.0
            self.position_pointer["price"] = float(recv["data"][0]["entryPrice"])
            self.position_pointer["qty"] = float(recv["data"][0]["size"])
            self.position_pointer["uPnl"] = float(recv["data"][0]["unrealisedPnl"])
            self.position_pointer["leverage"] = float(recv["data"][0]["leverage"])
import numpy as np
from typing import Dict

class BybitOrdersHandler:
    def __init__(self, private: Dict) -> None:
        self.private = private
        self._overwrite_ = ["Created", "New", "PartiallyFilled"]
        self._remove_ = ["Rejected", "Filled", "Cancelled"]

    def process(self, recv: Dict) -> Dict:
        E = float(recv["ts"])
        ts = float(recv["data"][0]["start"])

        # Prevent exchange pushing stale data
        if E >= ts: 
            for order in recv["data"]:
                if order["orderStatus"] in self._overwrite_:
                    self.private[order["symbol"]]["openOrders"][order["orderId"]] = {
                        "time": float(order["updatedTime"]),
                        "side": 0.0 if order["side"] == "Buy" else 1.0,
                        "price": float(order["price"]),
                        # "tp": None, NOTE: Add later...
                        "qty": float(order["qty"]),
                        "qtyRemaining": float(order["qty"]) - float(recv["leavesQty"]),
                    }

                elif order["orderStatus"] in self._remove_:
                    del self.private[order["symbol"]]["openOrders"][order["orderId"]]

                    if order["orderStatus"] == "Filled":
                        self.private[order["symbol"]]["executions"].append({
                            "orderId": float(order["orderId"]),
                            "time": float(order["updatedTime"]),
                            "side": 0.0 if order["side"] == "Buy" else 1.0,
                            "price": float(order["price"]),
                            # "tp": None, NOTE: Add later...
                            "qty": float(order["qty"]),
                        })
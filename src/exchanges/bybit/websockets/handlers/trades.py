
import numpy as np
from src.sharedstate import SharedState


class BybitTradesHandler:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    def _init(self, data) -> None:

        for row in data:
            side = 0 if row["side"] == "Buy" else 1
            trade = np.array([row["time"], side, row["price"], row["size"]], dtype=float)
            self.ss.bybit_trades.append(trade)


    def process(self, recv: dict) -> None:
        data = recv["data"]
        
        for trade in data:
            side = 0 if trade["S"] == "Buy" else 1
            new_trade = np.array([[trade["T"], side, trade["p"], trade["v"]]], dtype=float)
            self.ss.bybit_trades.append(new_trade)
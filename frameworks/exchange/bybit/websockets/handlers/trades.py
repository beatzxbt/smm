
import numpy as np
from frameworks.sharedstate.market import MarketDataSharedState


class BybitTradesHandler:


    def __init__(self, sharedstate: MarketDataSharedState, symbol: str) -> None:
        self.bybit = sharedstate.bybit[symbol]


    def initialize(self, data: list) -> None:
        for row in data:
            side = 0 if row["side"] == "Buy" else 1
            trade = np.array([row["time"], side, row["price"], row["size"]], dtype=float)
            self.bybit["trades"].append(trade)


    def update(self, recv: dict) -> None:
        for row in recv["data"]:
            side = 0 if row["S"] == "Buy" else 1
            trade = np.array([[row["T"], side, row["p"], row["v"]]], dtype=float)
            self.bybit["trades"].append(trade)
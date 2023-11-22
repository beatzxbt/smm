
import numpy as np
from frameworks.sharedstate.market import MarketDataSharedState


class HyperLiquidTradesHandler:


    def __init__(self, sharedstate: MarketDataSharedState, symbol: str) -> None:
        self.symbol = symbol
        self.hlq = sharedstate.hyperliquid[self.symbol]


    def initialize(self, data: list) -> None:
        for row in data:
            if not row["coin"] == self.symbol:
                continue

            side = 0 if row["side"] == "Buy" else 1 # Double check this with the raw feed
            trade = np.array([row["time"], side, row["px"], row["sz"]], dtype=float)
            self.hlq["trades"].append(trade)


    def update(self, recv: dict) -> None:
        for row in recv["data"]:
            if not recv["data"]["coin"] == self.symbol:
                continue

            side = 0 if row["side"] == "Buy" else 1 # Double check this with the raw feed
            trade = np.array([row["time"], side, row["px"], row["sz"]], dtype=float)
            self.hlq["trades"].append(trade)


import numpy as np
from frameworks.sharedstate.market import MarketDataSharedState


class HyperLiquidKlineHandler:


    def __init__(self, sharedstate: MarketDataSharedState, symbol: str) -> None:
        self.hlq = sharedstate.hyperliquid[symbol]


    def initialize(self, data: list) -> None:
        """
        Initialize the klines array
        """

        for candle in data:
            arr = np.array(candle, dtype=float)
            self.hlq["klines"].appendleft(arr)


    def update(self, recv: list) -> None:
        """
        Update the klines array 
        """

        for candle in recv["data"]:
            new = np.array(
                object=[
                    candle["start"],
                    candle["open"],
                    candle["high"],
                    candle["low"],
                    candle["close"],
                    candle["volume"],
                    candle["turnover"]], 
                dtype=float
            )

            # If prev time same, then overwrite, else append
            if self.hlq["klines"][-1][0] != new[0]:
                self.hlq["klines"].append(new)

            else:
                self.hlq["klines"].pop()
                self.hlq["klines"].append(new)

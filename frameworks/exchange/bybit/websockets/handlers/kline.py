
import numpy as np
from frameworks.sharedstate.market import MarketDataSharedState


class BybitKlineHandler:


    def __init__(self, sharedstate: MarketDataSharedState, symbol: str) -> None:
        self.bybit = sharedstate.bybit[symbol]


    def initialize(self, data: list) -> None:
        """
        Initialize the klines array
        """

        for candle in data:
            arr = np.array(candle, dtype=float)
            self.bybit["klines"].appendleft(arr)


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
            if self.bybit["klines"][-1][0] != new[0]:
                self.bybit["klines"].append(new)

            else:
                self.bybit["klines"].pop()
                self.bybit["klines"].append(new)

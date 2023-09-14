
import numpy as np

from src.indicators.bbw import bbw
from src.sharedstate import SharedState


class BybitKlineHandler:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    def _init(self, data: list) -> None:
        """
        Initialize the klines array and update volatility value
        """

        for candle in data:
            arr = np.array(candle, dtype=float)
            self.ss.bybit_klines.appendleft(arr)

        self.update_volatility()


    def process(self, recv: list) -> None:
        """
        Used to attain close values and calculate volatility
        """

        data = recv["data"]

        for candle in data:
            new = np.array([
                float(candle["start"]),
                float(candle["open"]),
                float(candle["high"]),
                float(candle["low"]),
                float(candle["close"]),
                float(candle["volume"]),
                float(candle["turnover"]),
            ])

            # If prev time same, then overwrite, else append
            if self.ss.bybit_klines[-1][0] != new[0]:
                self.ss.bybit_klines.append(new)

            else:
                self.ss.bybit_klines.pop()
                self.ss.bybit_klines.append(new)

            self.update_volatility()


    def update_volatility(self):

        self.ss.volatility_value = bbw(
            klines=self.ss.bybit_klines._unwrap(), 
            length=self.ss.bb_length, 
            multiplier=self.ss.bb_std
        )

        self.ss.volatility_value += self.ss.volatility_offset
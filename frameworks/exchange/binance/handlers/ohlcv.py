import numpy as np
from typing import List, Dict

from frameworks.exchange.base.ws_handlers.ohlcv import OhlcvHandler


class BinanceOhlcvHandler(OhlcvHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["ohlcv"])

    def refresh(self, recv: List[List]) -> None:
        for candle in recv:
            self.format[:] = np.array(candle[0:7], dtype=np.float64)
            self.ohlcv.append(self.format.copy())

    def process(self, recv: Dict) -> None:
        candle_open = float(recv["k"]["t"])
        new = True if candle_open > self.format[0] else False

        self.format[:] = np.array(
            [
                float(recv["k"]["t"]),
                float(recv["k"]["o"]),
                float(recv["k"]["h"]),
                float(recv["k"]["l"]),
                float(recv["k"]["c"]),
                float(recv["k"]["v"]),
                float(recv["k"]["q"]),
            ]
        )

        if not new:
            self.ohlcv.pop()

        self.ohlcv.append(self.format.copy())

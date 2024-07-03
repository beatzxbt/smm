import numpy as np
from typing import List, Dict

from frameworks.sharedstate import SharedState
from frameworks.exchange.base.ws_handlers.ohlcv import OhlcvHandler


class HyperliquidOhlcvHandler(OhlcvHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.ohlcv)
        
        self.current_open_time = 0

    def refresh(self, recv: List) -> None:
        for candle in recv:
            self.format[:] = np.array([
                float(candle["t"]),
                float(candle["o"]),
                float(candle["h"]),
                float(candle["l"]),
                float(candle["c"]),
                float(candle["v"])
            ])
            self.current_open_time = self.format[0]
            self.ohlcv.append(self.format.copy())
    
    def process(self, recv: Dict) -> None:
        time = float(recv["t"])
        new = True if time > self.current_open_time else False

        self.format[:] = np.array([
            time,
            float(recv["o"]),
            float(recv["h"]),
            float(recv["l"]),
            float(recv["c"]),
            float(recv["v"])
        ])

        if not new:
            self.ohlcv.pop()

        self.ohlcv.append(self.format.copy())
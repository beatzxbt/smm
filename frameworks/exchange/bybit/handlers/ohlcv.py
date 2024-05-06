import numpy as np
from typing import List, Dict

from frameworks.exchange.base.ws_handlers.ohlcv import OhlcvHandler
from frameworks.sharedstate import SharedState

class BybitOhlcvHandler(OhlcvHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.ohlcv)

    def initialize(self, recv: List[List]) -> None:
        for candle in recv:
            self.format[:] = np.array([
                float(candle["start"]),
                float(candle["open"]),
                float(candle["high"]),
                float(candle["low"]),
                float(candle["close"]),
                float(candle["volume"]),
                float(candle["turnover"])
            ])
            self.ohlcv.append(self.format.copy())
    
    def process(self, recv: Dict) -> None:
        latest_candle = recv["data"][0]
        ts = float(latest_candle["start"])
        new = True if ts > self.format[0] else False

        self.format[:] = np.array([
            ts,
            float(latest_candle["open"]),
            float(latest_candle["high"]),
            float(latest_candle["low"]),
            float(latest_candle["close"]),
            float(latest_candle["volume"]),
            float(latest_candle["turnover"])
        ])

        if not new:
            self.ohlcv.pop()

        self.ohlcv.append(self.format.copy())
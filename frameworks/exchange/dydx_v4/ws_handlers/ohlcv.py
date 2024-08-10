import numpy as np
from typing import List, Dict

from frameworks.exchange.base.ws_handlers.ohlcv import OHLCV, Candles, OhlcvHandler


class DydxOhlcvHandler(OhlcvHandler):
    def __init__(self, ohlcv: Candles) -> None:
        super().__init__(ohlcv)

    def refresh(self, recv: Dict) -> None:
        try:
            self.ohlcv.reset()

            new_candles: List[OHLCV] = []

            for candle in recv["candles"]:
                new_candles.append(OHLCV(
                    timestamp=float(candle["startedAt"]),
                    open=float(candle["open"]),
                    high=float(candle["high"]),
                    low=float(candle["low"]),
                    close=float(candle["close"]),
                    volume=float(candle["baseTokenVolume"]),
                ))

            self.ohlcv.add_many(new_candles)

        except Exception as e:
            raise Exception(f"OHLCV refresh - {e}")

    def process(self, recv) -> None:
        # No OHLCV stream available, or planned for this exchange
        pass

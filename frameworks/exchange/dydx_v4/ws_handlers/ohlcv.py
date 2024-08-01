import numpy as np
from typing import List, Dict

from frameworks.exchange.base.ws_handlers.ohlcv import OhlcvHandler


class DydxOhlcvHandler(OhlcvHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["ohlcv"])

    def refresh(self, recv: Dict) -> None:
        try:
            self.clear_ohlcv_ringbuffer()
            for candle in recv["candles"]:
                self.ohlcv.append(np.array(
                    [
                        float(candle["startedAt"]),
                        float(candle["open"]),
                        float(candle["high"]),
                        float(candle["low"]),
                        float(candle["close"]),
                        float(candle["baseTokenVolume"]),
                    ]
                ))

        except Exception as e:
            raise Exception(f"OHLCV refresh - {e}")

    def process(self, recv) -> None:
        # No OHLCV stream available, or planned for this exchange
        pass

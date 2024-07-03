import numpy as np
from typing import List, Dict

from frameworks.exchange.base.ws_handlers.ohlcv import OhlcvHandler


class OkxOhlcvHandler(OhlcvHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["ohlcv"])

    def refresh(self, recv: Dict) -> None:
        try:
            self.clear_ohlcv_ringbuffer()
            for candle in recv["data"]:
                self.format[:] = np.array(
                    [
                        float(candle[0]),
                        float(candle[1]),
                        float(candle[2]),
                        float(candle[3]),
                        float(candle[4]),
                        float(candle[5]),
                    ]
                )
                self.ohlcv.append(self.format.copy())

        except Exception as e:
            raise Exception(f"[OHLCV refresh] {e}")

    def process(self, recv: Dict) -> None:
        try:
            for candle in recv["data"]:
                ts = float(candle[0])
                new = True if ts > self.format[0] else False

                self.format[:] = np.array(
                    [
                        ts,
                        float(candle[1]),
                        float(candle[2]),
                        float(candle[3]),
                        float(candle[4]),
                        float(candle[5]),
                    ]
                )

                if not new:
                    self.ohlcv.pop()

                self.ohlcv.append(self.format.copy())

        except Exception as e:
            raise Exception(f"[OHLCV process] {e}")

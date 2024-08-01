import numpy as np
from typing import List, Dict, Any

from frameworks.exchange.base.ws_handlers.ohlcv import OHLCV, Candles, OhlcvHandler


class BybitOhlcvHandler(OhlcvHandler):
    def __init__(self, ohlcv: Candles) -> None:
        super().__init__(ohlcv)

    def refresh(self, recv: Dict[str, Any]) -> None:
        try:
            self.ohlcv.reset()

            new_candles: List[OHLCV] = []

            for candle in recv["result"]["list"]:
                new_candles.append(OHLCV(
                    timestamp=float(candle[0]),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[6]),
                ))

            self.ohlcv.add_many(new_candles)

        except Exception as e:
            raise Exception(f"OHLCV refresh - {e}")

    def process(self, recv: Dict[str, Any]) -> None:
        try:
            for candle in recv["data"]:
                new_candle = OHLCV(
                    timestamp=float(candle.get("start")),
                    open=float(candle.get("open")),
                    high=float(candle.get("high")),
                    low=float(candle.get("low")),
                    close=float(candle.get("close")),
                    volume=float(candle.get("volume")),
                )

                self.ohlcv.add_single(new_candle)

        except Exception as e:
            raise Exception(f"OHLCV process - {e}")

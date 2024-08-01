import numpy as np
from typing import List, Dict, Any

from frameworks.exchange.base.ws_handlers.ohlcv import OHLCV, Candles, OhlcvHandler


class BinanceOhlcvHandler(OhlcvHandler):
    def __init__(self, ohlcv: Candles) -> None:
        super().__init__(ohlcv)

    def refresh(self, recv: List[List]) -> None:
        try:
            self.ohlcv.reset()
            
            new_candles: List[OHLCV] = []

            for candle in recv:
                new_candles.append(OHLCV(
                    timestamp=float(candle[0]),
                    open=float(candle[1]),
                    high=float(candle[2]),
                    low=float(candle[3]),
                    close=float(candle[4]),
                    volume=float(candle[5])
                ))

            self.ohlcv.add_many(new_candles)

        except Exception as e:
            raise Exception(f"OHLCV refresh - {e}")

    def process(self, recv: Dict[str, Any]) -> None:
        try:
            candle: Dict[str, str] = recv["k"]
            
            self.ohlcv.add_single(OHLCV(
                timestamp=float(candle.get("t")),
                open=float(candle.get("o")),
                high=float(candle.get("h")),
                low=float(candle.get("l")),
                close=float(candle.get("c")),
                volume=float(candle.get("v"))
            ))

        except Exception as e:
            raise Exception(f"OHLCV process - {e}")

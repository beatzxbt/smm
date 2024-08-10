import numpy as np
from typing import List, Dict, Any

from frameworks.exchange.base.ws_handlers.ohlcv import OHLCV, Candles, OhlcvHandler


class HyperliquidOhlcvHandler(OhlcvHandler):
    def __init__(self, ohlcv: Candles) -> None:
        super().__init__(ohlcv)

    def refresh(self, recv: List[Dict]) -> None:
        try:
            self.ohlcv.reset()

            new_candles: List[OHLCV] = []

            for candle in recv:
                new_candles.append(OHLCV(
                    timestamp=float(candle["t"]),
                    open=float(candle["o"]),
                    high=float(candle["h"]),
                    low=float(candle["l"]),
                    close=float(candle["c"]),
                    volume=float(candle["v"]),
                ))

            self.ohlcv.add_many(new_candles)

        except Exception as e:
            raise Exception(f"OHLCV refresh - {e}")
        
    def process(self, recv: Dict[str, Any]) -> None:
        try:
            new_candle = OHLCV(
                timestamp=float(recv.get("t")),
                open=float(recv.get("o")),
                high=float(recv.get("h")),
                low=float(recv.get("l")),
                close=float(recv.get("c")),
                volume=float(recv.get("v")),
            )

            self.ohlcv.add_single(new_candle)

        except Exception as e:
            raise Exception(f"OHLCV process - {e}")
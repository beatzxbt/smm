import numpy as np
from numpy_ringbuffer import RingBuffer
from typing import List, Dict

class BybitOhlcvHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market
        self._cache_ = np.array([[1e10, 1e-3, 1e-3, 1e-3, 1e-3, 1e-3]], dtype=float)
        self.ohlcv_pointer = None

    def initialize(self, recv: List) -> RingBuffer:
        if self.ohlcv_pointer is None:
            self.ohlcv_pointer = self.market[recv["s"]]["ohlcv"]

        for row in recv:
            self._cache_[0, 0] = float(row["start"])
            self._cache_[0, 1] = float(row["open"])
            self._cache_[0, 2] = float(row["high"])
            self._cache_[0, 3] = float(row["low"])
            self._cache_[0, 4] = float(row["close"])
            self._cache_[0, 5] = float(row["volume"])
            self._cache_[0, 6] = float(row["turnover"])
            self.ohlcv_pointer.appendleft(self._cache_.copy())

        self.latest_candle = self._cache_[0, 0]

    def process(self, recv: Dict) -> RingBuffer:
        if self.ohlcv_pointer is None:
            self.ohlcv_pointer = self.market[recv["s"]]["ohlcv"]

        E = float(recv["ts"])
        ts = float(recv["data"][0]["start"])

        # Avoid exchange pushing stale data
        if E >= ts: 
            self._cache_[0, 0] = ts
            self._cache_[0, 1] = float(recv["data"][0]["open"])
            self._cache_[0, 2] = float(recv["data"][0]["high"])
            self._cache_[0, 3] = float(recv["data"][0]["low"])
            self._cache_[0, 4] = float(recv["data"][0]["close"])
            self._cache_[0, 5] = float(recv["data"][0]["volume"])
            self._cache_[0, 6] = float(recv["data"][0]["turnover"])
            self.ohlcv_pointer.append(self._cache_.copy())
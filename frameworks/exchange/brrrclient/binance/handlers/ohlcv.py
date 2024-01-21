import numpy as np
from numpy_ringbuffer import RingBuffer
from typing import List, Dict

class BinanceOhlcvHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market
        self._cache_ = np.array([[1e10, 1e-3, 1e-3, 1e-3, 1e-3, 1e-3]], dtype=float)

    def initialize(self, symbol: str, recv: List) -> RingBuffer:
        for row in recv:
            self._cache_[0, 0] = float(row[0])
            self._cache_[0, 1] = float(row[1])
            self._cache_[0, 2] = float(row[2])
            self._cache_[0, 3] = float(row[3])
            self._cache_[0, 4] = float(row[4])
            self._cache_[0, 5] = float(row[5])
            self._cache_[0, 6] = float(row[6])
            self.latest_timestamp = row[0]
            self.market[symbol]["ohlcv"].append(self._cache_.copy())

    def process(self, recv: Dict) -> RingBuffer:
        E = float(recv["E"])
        ts = float(recv["k"]["t"])

        # Prevent exchange pushing stale data
        if E >= ts: 
            self._cache_[0, 0] = ts
            self._cache_[0, 1] = float(recv["k"][1])
            self._cache_[0, 2] = float(recv["k"][2])
            self._cache_[0, 3] = float(recv["k"][3])
            self._cache_[0, 4] = float(recv["k"][4])
            self._cache_[0, 5] = float(recv["k"][5])
            self._cache_[0, 6] = float(recv["k"][6])
            self.market[recv["s"]]["ohlcv"].append(self._cache_.copy())
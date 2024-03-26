import numpy as np
from numpy_ringbuffer import RingBuffer
from typing import List, Dict, Union

class BinanceTradesHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market
        self._cache_ = np.array([[1e10, 0.0, 1e-3, 1e-3]], dtype=float)

    def initialize(self, symbol: str, recv: List) -> RingBuffer:
        for row in recv:
            self._cache_[0, 0] = row["time"]
            self._cache_[0, 1] = 1.0 if row["isBuyerMaker"] else 0.0
            self._cache_[0, 2] = row["price"]
            self._cache_[0, 3] = row["qty"]
            self.market[symbol]["trades"].append(self._cache_.copy())

    def process(self, recv: Union[Dict, List, str]) -> RingBuffer:
        self._cache_[0, 0] = recv["data"]["T"]
        self._cache_[0, 1] = 1.0 if recv["data"]["m"] else 0.0
        self._cache_[0, 2] = recv["data"]["p"]
        self._cache_[0, 3] = recv["data"]["q"]
        self.market[recv["s"]]["trades"].append(self._cache_.copy())
import numpy as np
from numpy_ringbuffer import RingBuffer
from typing import List, Dict, Union

class BybitTradesHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market
        self._cache_ = np.array([[1e10, 0.0, 1e-3, 1e-3]], dtype=float)
        self.trades_pointer = None

    def initialize(self, recv: List) -> RingBuffer:
        if self.trades_pointer is None:
            self.trades_pointer = self.market[recv[0]["symbol"]]["trades"]

        for row in recv:
            self._cache_[0, 0] = float(row["time"])
            self._cache_[0, 1] = 0.0 if row["side"] == "Buy" else 1.0
            self._cache_[0, 2] = float(row["price"])
            self._cache_[0, 3] = float(row["size"])
            self.trades_pointer.append(self._cache_.copy())

    def process(self, recv: Union[Dict, List, str]) -> RingBuffer:
        if self.trades_pointer is None:
            self.trades_pointer = self.market[recv["data"]["s"]]["trades"]

        self._cache_[0, 0] = float(recv["data"]["T"])
        self._cache_[0, 1] = 0.0 if recv["data"]["S"] == "Buy" else 1.0
        self._cache_[0, 2] = float(recv["data"]["p"])
        self._cache_[0, 3] = float(recv["data"]["v"])
        self.trades_pointer.append(self._cache_.copy())
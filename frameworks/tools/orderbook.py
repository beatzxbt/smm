import numpy as np
from typing import List, Union
from numpy.typing import NDArray
from frameworks.tools.logger import ms as time_ms


class Orderbook:
    """NEEDS FIXING"""

    def __init__(self, size: int):
        self.size = size
        self.asks = np.empty(shape=(self.size, 2), dtype=float)
        self.bids = np.empty_like(self.asks)
        self.last_update = time_ms()

    def _sort_book_(self) -> NDArray:
        """Sort bids & asks"""
        self.asks = self.asks[self.asks[:, 0].argsort()][:self.size]
        self.bids = self.bids[self.bids[:, 0].argsort()][::-1][:self.size]

    def _process_book_(book: NDArray, new_data: List[List[float]]) -> NDArray:
        book = book[~np.isin(
            book[:, 0],
            np.concatenate([
                new_data[new_data[:, 1] == 0, 0],
                new_data[:, 0]
            ])
        )]
        non_zero_qty_new_data = new_data[new_data[:, 1] != 0]
        return np.vstack((book, non_zero_qty_new_data))

    def initialize(self, asks: List[List[float]], bids: List[List[float]]) -> NDArray:
        """Replace current ask, bid slots, then sort"""
        self.asks = np.array(asks, dtype=float)
        self.bids = np.array(bids, float)
        self._sort_book_()

    def update(self, asks: List[List[float]], bids: List[List[float]], timestamp: Union[int, float]) -> NDArray:
        """Update asks or bids with new levels, remove ones with qty=0, then sort"""
        if timestamp > self.last_update:
            self.last_update = timestamp
            asks = np.array(asks, dtype=float)
            bids = np.array(bids, dtype=float)
            self.asks = self._process_book_(self.asks, asks)
            self.bids = self._process_book_(self.bids, bids)
            self._sort_book_()
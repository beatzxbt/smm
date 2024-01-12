import numpy as np
from numpy.typing import NDArray


class OrderBook:
    """Requires testing"""
    arr_float64_T = NDArray[np.float64]

    def __init__(self, size: int):
        self.size = size
        self.asks = np.empty(shape=(self.size, 2), dtype=float)
        self.bids = np.empty_like(self.asks)

    def _sort_book_(self) -> arr_float64_T:
        """Sort full book"""
        self.asks = self.asks[self.asks[:, 0].argsort()][:self.size]
        self.bids = self.bids[self.bids[:, 0].argsort()[::-1]][:self.size]

    def initialize(self, asks: arr_float64_T, bids: arr_float64_T) -> arr_float64_T:
        """Replace current ask, bid slots and sort"""
        self.asks = asks
        self.bids = bids
        self._sort_book_()

    def update(self, asks: arr_float64_T, bids: arr_float64_T) -> arr_float64_T:
        """Update asks and bids with new levels, remove ones with qty=0 and sort"""

        def process_book(book, new_data):
            book = book[~np.isin(
                book[:, 0],
                np.concatenate([
                    new_data[new_data[:, 1] == 0, 0],
                    new_data[:, 0]
                ])
            )]
            non_zero_qty_new_data = new_data[new_data[:, 1] != 0]
            return np.vstack((book, non_zero_qty_new_data))

        self.asks = process_book(self.asks, asks)
        self.bids = process_book(self.bids, bids)
        self._sort_book_()
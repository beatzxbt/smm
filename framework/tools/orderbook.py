import numpy as np
from numba import njit
from numba.experimental import jitclass
from numba.types import uint64, float64, bool_

@njit(inline="always")
def isin(a: np.ndarray, b: np.ndarray) -> np.ndarray[bool]:
    """
    Constaints:
    * 'a': dim=1, dtype='same as b'
    * 'b': dim=1, dtype='same as a'
    """
    assert a.ndim == 1 and b.ndim == 1, "2D arrays not supported."

    b_set = set(b)
    out_len = a.size
    out = np.empty(out_len, dtype=bool_)
    for i in range(out_len):
        out[i] = a[i] in b_set

    return out

@njit(inline="always")
def roll(a: np.ndarray, shift: int, axis: int) -> np.ndarray:
    """
    Constraints:
    * 'axis': int >= 0
    """
    assert axis >= 0, "Axis must be positive."

    if shift == 0:
        return a

    if a.ndim == 1:
        if shift > 0:
            return np.concat((a[-shift:], a[:-shift]))
        else:
            return np.concat((a[shift:], a[:shift]))

    # Numba throws index error without this. Seems that it cant
    # infer the early return from ndim==1 branch and fails to
    # generate the memory map correctly for 'a'
    assert a.ndim > 1

    shift = shift % a.shape[axis]

    out = np.empty_like(a)
    axis_len = a.shape[axis]

    # Roll the array
    for i in range(axis_len):
        new_index = (i + shift) % axis_len
        if axis == 0:
            out[new_index, :] = a[i, :]
        else:
            out[:, new_index] = a[:, i]

    return out

@jitclass
class Orderbook:
    """
    An orderbook class, maintaining separate arrays for bid and
    ask orders with functionality to initialize, update, and sort
    the orders.

    The data fed into the orderbook is expected to be in the following format:
    - Bids: [[px, sz], ...]
    - Asks: [[px, sz], ...]

    The orderbook will then sort the bids and asks in descending order of price
    for the bids and ascending order of price for the asks.
    
    It assumes the data is in chronological order, and thus doesn't keep track
    of the sequence id. Sort this out directly in the data feeds!
    """
 
    _size: uint64
    _is_warm: bool_
    _asks: float64[:, :]
    _bids: float64[:, :]

    def __init__(self, size: int) -> None:
        if size <= 1:
            raise ValueError(f"Invalid size; expected >1 but got {size}")

        self._size: int = size
        self._is_warm: bool = False
        self._asks: np.ndarray = np.zeros((size, 2), dtype=float64)
        self._bids: np.ndarray = np.zeros((size, 2), dtype=float64)

    def _sort_bids(self, bids: np.ndarray) -> None:
        """
        Removes entries with matching prices in update, regardless of size, and then
        adds non-zero quantity data from update to the book.

        Sorts the bid orders in descending order of price.

        If the best bid is higher than any asks, remove those asks by:
         - Filling the to-be removed arrays with zeros.
         - Rolling it to the back of the orderbook.
        """
        removed_old_prices = self._bids[~isin(self._bids[:, 0], bids[:, 0])]
        new_full_bids = np.vstack(
            (
                removed_old_prices[
                    removed_old_prices[:, 1] != 0.0  # Re-remove zeros incase of overlap
                ],
                bids[bids[:, 1] != 0.0],
            )
        )

        self._bids = new_full_bids[new_full_bids[:, 0].argsort()][::-1][: self._size]

        # Remove overlapping asks.
        if self._bids[0, 0] >= self._asks[0, 0]:
            overlapping_asks = self._asks[self._asks[:, 0] <= self._bids[0, 0]].shape[0]
            self._asks[:overlapping_asks].fill(0.0)
            self._asks[:, :] = roll(self._asks, -overlapping_asks, 0)

    def _sort_asks(self, asks: np.ndarray) -> None:
        """
        Removes entries with matching prices in update, regardless of size, and then
        adds non-zero quantity data from update to the book.

        Sorts the ask orders in ascending order of price.

        If the best ask is lower than any bids, remove those bids by:
         - Filling the to-be removed arrays with zeros.
         - Rolling it to the back of the orderbook.
        """
        removed_old_prices = self._asks[~isin(self._asks[:, 0], asks[:, 0])]
        new_full_asks = np.vstack(
            (
                removed_old_prices[
                    removed_old_prices[:, 1] != 0.0  # Re-remove zeros incase of overlap
                ],
                asks[asks[:, 1] != 0.0],
            )
        )

        self._asks = new_full_asks[new_full_asks[:, 0].argsort()][: self._size]

        # Remove overlapping bids.
        if self._asks[0, 0] <= self._bids[0, 0]:
            overlapping_bids = self._bids[self._bids[:, 0] >= self._asks[0, 0]].shape[0]
            self._bids[:overlapping_bids].fill(0.0)
            self._bids[:, :] = roll(self._bids, -overlapping_bids, 0)

    def reset(self, asks: np.ndarray, bids: np.ndarray) -> None:
        """
        Refreshes the order book with given *complete* ask and bid data and sorts the book.

        Parameters
        ----------
        asks : np.ndarray
            Initial ask orders data, formatted as [[px, sz], ...].

        bids : np.ndarray
            Initial bid orders data, formatted as [[px, sz], ...].
        """
        # Reset attributes and internal arrays.
        self._is_warm = False
        self._asks.fill(0.0)
        self._bids.fill(0.0)

        # Prefer to broadcast onto internal arrays, not overwrite.
        # We also assume that they come in without any overlapping bids/asks,
        # skipping that check and previous array stacking for perf.
        self._asks[:, :] = asks[asks[:, 0].argsort()]
        self._bids[:, :] = bids[bids[:, 0].argsort()[::-1]]

        self._is_warm = True

    def update_bbo(
        self,
        bid_px: float,
        bid_sz: float,
        ask_px: float,
        ask_sz: float,
    ) -> None:
        """
        Updates the current orderbook with new best bid ask data.
        """
        self.ensure_warm()

        best_bid_price = self._bids[0, 0]
        best_ask_price = self._asks[0, 0]

        # Matching bid price, update size.
        if bid_px == best_bid_price:
            if bid_sz == 0.0:
                # Most feeds don't send size 0 through the BBA
                # feed, but just incase, this case is included.
                # It is inefficient due to the realloc, but wont
                # be optimized further.
                self._bids = self._bids[1:]
            else:
                self._bids[0, 1] = bid_sz

        # Higher bid price, insert ontop then solve ask overlaps.
        elif bid_px > best_bid_price:
            self._bids = roll(self._bids, 1, 0)
            self._bids[0, 0] = bid_px
            self._bids[0, 1] = bid_sz

            # Remove overlapping asks (identical to self._sort_bids())
            if self._bids[0, 0] >= self._asks[0, 0]:
                overlapping_asks = self._asks[
                    self._asks[:, 0] <= self._bids[0, 0]
                ].shape[0]
                self._asks[:overlapping_asks].fill(0.0)
                self._asks[:, :] = roll(self._asks, -overlapping_asks, 0)

        # Matching ask price, update size.
        if ask_px == best_ask_price:
            if ask_sz == 0.0:
                # Most feeds don't send size 0 through the BBA
                # feed, but just incase, this case is included.
                # It is inefficient due to the realloc, but wont
                # be optimized further.
                self._asks = self._asks[1:]
            else:
                self._asks[0, 1] = ask_sz

        # Lower ask price, insert ontop then solve bid overlaps.
        elif ask_px < best_ask_price:
            self._asks = roll(self._asks, 1, 0)
            self._asks[0, 0] = ask_px
            self._asks[0, 1] = ask_sz

            # Remove overlapping bids (identical to self._sort_asks()).
            if self._asks[0, 0] <= self._bids[0, 0]:
                overlapping_bids = self._bids[
                    self._bids[:, 0] >= self._asks[0, 0]
                ].shape[0]
                self._bids[:overlapping_bids].fill(0.0)
                self._bids[:, :] = roll(self._bids, -overlapping_bids, 0)

    def update_bids(self, new_bids: np.ndarray) -> None:
        """
        Updates the current bids with new data.

        Parameters
        ----------
        bids : np.ndarray
            New bid orders data, formatted as [[price, size], ...].
        """ 
        self.ensure_warm()
        self._sort_bids(new_bids)

    def update_asks(self, new_asks: np.ndarray) -> None:
        """
        Updates the current asks with new data.

        Parameters
        ----------
        asks : np.ndarray
            New ask orders data, formatted as [[price, size], ...].
        """
        self.ensure_warm()
        self._sort_asks(new_asks)

    def update_full(self, new_asks: np.ndarray, new_bids: np.ndarray) -> None:
        """
        Updates the order book with new ask and bid data.

        Parameters
        ----------
        asks : np.ndarray
            New ask orders data, formatted as [[price, size], ...].

        bids : np.ndarray
            New bid orders data, formatted as [[price, size], ...].
        """
        self.ensure_warm()
        self._sort_bids(new_bids)
        self._sort_asks(new_asks)

    def get_mid_px(self) -> float:
        """
        Return the midpoint between the best bid and best ask prices.

        Returns:
            float: 
                The midpoint, calculated as (best_bid + best_ask) / 2.0.

        Raises:
            RuntimeError: If the orderbook is not warmed (caught via `ensure_warm()`).
        """
        self.ensure_warm()
        return (self._bids[0, 0] + self._asks[0, 0]) / 2.0

    def get_wmid_px(self):
        """
        Return a 'weighted mid' price considering size at the top bid and ask.

        This method computes an imbalance ratio based on the top bid size and top ask size, 
        and uses that ratio to do a linear interpolation between best_bid and best_ask prices.

        Returns:
            float:
                The weighted mid, computed as 
                (best_bid_price * imbalance + best_ask_price * (1 - imbalance)),
                where imbalance = top_bid_size / (top_bid_size + top_ask_size).

        Raises:
            RuntimeError: If the orderbook is not warmed (caught via `ensure_warm()`).
        """
        self.ensure_warm()
        top_bid_sz = self._bids[0, 1]
        top_ask_sz = self._asks[0, 1]
        imbalance = top_bid_sz / (top_bid_sz + top_ask_sz)
        return (self._bids[0, 0] * imbalance) + (self._asks[0, 0] * (1.0 - imbalance))

    def get_bbo_spread(self):
        """
        Calculate the spread between the best ask and the best bid.

        Returns:
            float: The difference between the best ask price (asks[0,0])
                and the best bid price (bids[0,0]).
        """
        self.ensure_warm()
        return self._asks[0, 0] - self._bids[0, 0]
    
    # ----- Public array access methods ----- #

    def get_bids(self) -> np.ndarray:
        """
        Return the entire bids array.

        Returns:
            np.ndarray: The NumPy array representing the bid side 
                of the orderbook.
        """
        return self._bids

    def get_asks(self) -> np.ndarray:
        """
        Return the entire asks array.

        Returns:
            np.ndarray: The NumPy array representing the ask side 
                of the orderbook.
        """
        return self._asks

    def get_bbo(self) -> np.ndarray:
        """
        Return the current best bid and best ask in a single array.

        Returns:
            np.ndarray: A NumPy array of shape (2, 2), where:
                [0] => best bid [price, size]
                [1] => best ask [price, size]
        """
        return np.array([self._bids[0], self._asks[0]])

    # ----- Fast sanity checkers ----- #

    def is_warm(self) -> bool:
        """
        Check if the orderbook is considered 'warm' (i.e., has been initialized).

        Returns:
            bool: True if warmed up, False otherwise.
        """
        return self._is_warm

    def ensure_warm(self):
        """
        Raise an error if the orderbook is not 'warm'.

        Raises:
            RuntimeError: If the orderbook is not initialized via '.reset()'.
        """
        if not self._is_warm:
            raise RuntimeError(
                "Orderbook not populated; must call '.reset()' before proceeding"
            )
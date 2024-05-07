import numpy as np
from numba import njit
from numba.types import Array

@njit(["float64(float64[:, :], int64)"], error_model="numpy", fastmath=True)
def trades_diffs(trades: Array, lookback: int=100) -> float:
    """
    Computes the sum of the absolute differences of trade prices over a specified lookback period.
    
    Steps:
        -> Filter out prices from the trades array.
        -> Compute absolute differences element-by-element.
        -> Sum those differences then return.

    Parameters
    ----------
    trades : Array
        The trades array from the sharedstate, in the format [Time, Side, Price, Size].

    lookback : int, optional
        The number of recent trades to consider for calculating the price differences. The default is 100.

    Returns
    -------
    float
        The sum of the absolute differences in trade prices for the specified number of recent trades.
    """
    prices = trades[-lookback:, 2]
    abs_diff = np.abs(np.diff(prices))
    return abs_diff.sum()

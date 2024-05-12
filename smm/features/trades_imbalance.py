import numpy as np
from numba import njit
from numba.types import Array

from frameworks.tools.trading.weights import generate_geometric_weights


@njit(["float64(float64[:, :], int64)"], error_model="numpy", fastmath=True)
def trades_imbalance(trades: Array, window: int) -> float:
    """
    Calculates the normalized imbalance between buy and sell trades within a specified window,
    using geometrically weighted quantities. The imbalance reflects the dominance of buy or sell trades,
    weighted by the recency of trades in the window.

    Steps:
    1. Determine the effective window size, the lesser of the specified window or the total trades count.

    2. Generate geometric weights for the effective window size, with recent trades given higher significance.

    3. Iterate through the trades within the window, applying the weights to the log of (1 + trade quantity)
       to calculate weighted trade quantities. Separate cumulative totals are maintained for buys and sells based
       on the trade side.

    4. Compute the normalized imbalance as the difference between cumulative buy and sell quantities divided
       by their sum, yielding a measure from -1 (sell dominance) to 1 (buy dominance).

    Parameters
    ----------
    trades : Array
        A 2D array of trade data, where each row represents a trade in format [time, side, price, size]

    window : int
        The number of most recent trades to consider for the imbalance calculation.

    Returns
    -------
    float
        The normalized imbalance, ranging from -1 (complete sell dominance) to 1 (complete buy dominance).

    Examples
    --------
    >>> trades = np.array([
    ...     [1e10, 0.0, 100.75728, 0.70708],
    ...     [1e10, 1.0, 100.29356, 0.15615],
    ...     [1e10, 0.0, 100.76157, 0.94895],
    ...     [1e10, 1.0, 100.46078, 0.23170],
    ...     [1e10, 0.0, 100.18463, 0.87096]
    ... ])
    >>> window = 5
    >>> print(trades_imbalance(trades, window))
    -0.7421903970691232
    """
    window = min(window, trades.shape[0])
    weights = generate_geometric_weights(window)
    delta_buys = 0.0
    delta_sells = 0.0

    for i in range(window):
        trade_side = trades[i, 1]
        weighted_qty = np.log(1.0 + trades[i, 3]) * weights[i]

        if trade_side == 0.0:
            delta_buys += weighted_qty
        else:
            delta_sells += weighted_qty

    return (delta_buys - delta_sells) / (delta_buys + delta_sells)

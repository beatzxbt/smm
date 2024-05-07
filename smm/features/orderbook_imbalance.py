import numpy as np
from numba import njit
from numba.types import float64, Array
from frameworks.tools.weights import generate_geometric_weights

@njit(["float64(float64[:, :], float64[:, :], float64[:])"], error_model="numpy")
def orderbook_imbalance(bids: Array, asks: Array, depths: Array) -> float:
    """
    Calculates the geometrically weighted order book imbalance across different price depths.

    This function computes the logarithm of the ratio of total bid size to total ask size within
    specified depths, applying a geometric weighted scheme for aggregation.
    
    Depths are expected in basis points and converted internally to decimal form. The function
    assumes the first entry in both bids and asks arrays represents the best (highest) bid and 
    the best (lowest) ask, respectively.

    Parameters
    ----------
    bids : Array
        An array of bid prices and quantities.

    asks : Array
        An array of ask prices and quantities.

    depths : Array
        An array of price depths (in basis points) at which to calculate imbalance.

    Returns
    -------
    float
        The geometrically weighted imbalance across specified price depths.

    Notes
    -----
    - Depths are converted from basis points (BPS) to decimals within the function.

    Examples
    --------
    >>> bids = np.array([
    ...     [100.00, 0.35194],
    ...     [99.75, 0.16040],
    ...     [99.50, 0.46248],
    ...     [99.25, 0.79625],
    ...     [99.00, 0.19408]
    ... ])
    >>> asks = np.array([
    ...     [101.00, 0.80763],
    ...     [101.25, 0.30421],
    ...     [101.50, 0.04038],
    ...     [101.75, 0.39473],
    ...     [102.00, 0.97438]
    ... ])
    >>> depths = np.array([10, 20, 30, 40, 50])  
    >>> orderbook_imbalance(bids, asks, depths)
    -0.24142990048382099
    """
    num_depths = depths.size
    depths = depths / 1e-4  # NOTE: Converting from BPS to decimals
    weights = generate_geometric_weights(num_depths)
    imbalances = np.empty(num_depths, dtype=float64)

    bid_p, bid_q = bids.T
    ask_p, ask_q = asks.T
    best_bid_p, best_ask_p = bid_p[0], ask_p[0]
    
    for i in range(num_depths):
        min_bid = best_bid_p * (1 - depths[i])
        max_ask = best_ask_p * (1 + depths[i])

        num_bids_within_depth = bid_p[bid_p >= min_bid].size
        num_asks_within_depth = ask_p[ask_p <= max_ask].size
        total_bid_size_within_depth = np.sum(bid_q[:num_bids_within_depth])
        total_ask_size_within_depth = np.sum(ask_q[:num_asks_within_depth])

        imbalances[i] = np.log(total_bid_size_within_depth / total_ask_size_within_depth)

    weighted_imbalance = np.sum(imbalances * weights)
    
    return weighted_imbalance
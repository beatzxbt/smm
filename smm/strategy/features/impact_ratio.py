import numpy as np
from numba import njit
from numpy.typing import NDArray

@njit(cache=True)
def impact_ratio(trades: NDArray, tick_size: float) -> float:
    """Trade: [ts, side, price, qty]"""
    unique_timestamps = np.unique(trades[:, 0])
    p_stale, p_impact = 0, 0

    for timestamp in unique_timestamps:
        batched_trades = trades[trades[:, 0] == timestamp]
        if batched_trades.size == 4:
            p_stale += tick_size            
        else:
            p_impact += np.abs(batched_trades[0, 2] - batched_trades[-1, 2])
            
    return p_impact/p_stale

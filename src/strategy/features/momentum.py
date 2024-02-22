import numpy as np
from numba import njit
from numpy.typing import NDArray
from src.indicators.ema import ema


@njit
def momentum_v1(klines: NDArray, lengths: NDArray) -> float:
    """
    Make sure lengths are fed in from longest to shortest
    """
    closes = klines[:, 4]
    n = lengths.size
    vals = np.empty(n, dtype=np.float64)

    for i in range(n):
        length = lengths[i]
        ema_val = ema(closes[-length:], length)[-1]

        # Safety check
        if ema_val == 0:
            vals[i] = vals[i-1]   
        else:
            vals[i] = np.log(closes[-1] / ema_val) * 100

    trend_val = ema(vals, n)
    return np.sum(trend_val)
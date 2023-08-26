
import numpy as np
from numba import njit
from src.indicators.ema import ema


@njit
def trend_feature(klines, lengths):
    """
    Make sure lengths are fed in from longest to shortest
    """

    closes = klines[:, 4]
    curr_price = closes[-1]
    n = len(lengths)
    vals = np.empty(n, dtype=float)

    for i in range(n):
        length = lengths[i]
        ema_val = ema(closes[-length:], length)[-1]

        vals[i] = np.log(curr_price/ema_val) * 100

    trend_val = ema(vals, n)[-1]

    return trend_val
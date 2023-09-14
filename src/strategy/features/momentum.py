
import numpy as np
from numba import njit
from src.indicators.ema import ema


@njit
def trend_feature(klines: np.ndarray, lengths: np.ndarray) -> float:
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

        # Safety check
        if ema_val == 0:
            vals[i] = vals[i-1]   

        else:
            vals[i] = np.log(curr_price / ema_val) * 100

    trend_val = ema(vals, n)

    return np.sum(trend_val)


@njit
def trend_feature_v2(klines: np.ndarray, lengths: np.ndarray) -> float:
    """
    V2 normalizes the trend further, with improved reversals

    Make sure lengths are fed in from longest to shortest
    """

    closes = klines[:, 4]
    curr_price = closes[-1]
    n = len(lengths)
    vals = np.empty(n, dtype=float)

    for i in range(n):
        length = lengths[i]
        ema_val = ema(closes[-length:], length)[-1]

        # Safety check
        if ema_val == 0:
            vals[i] = vals[i-1]   

        else:
            vals[i] = np.log(curr_price / ema_val) * 100

    trend_val = ema(vals, n)
    smoothed_trend_val = ema(trend_val, 3)
    base_trend_filter = ema(smoothed_trend_val, 20)

    spread = smoothed_trend_val[-1] - base_trend_filter[-1]

    return spread

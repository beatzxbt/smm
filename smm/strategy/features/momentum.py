
import numpy as np
from numba import njit
from smm.indicators.ema import ema


@njit
def ema_weights(window: int) -> np.ndarray:
    """
    Calculate EMA-like weights of given window size.
    """

    alpha = 2 / float(window + 1)
    weights = np.empty(window, dtype=float)

    for i in range(window):
        weights[i] = alpha * (1 - alpha) ** i

    return weights[::-1]


@njit
def _tick_candles(trades: np.ndarray, bucket_size: int) -> np.ndarray:
    n_candles = int(trades.shape[0]/bucket_size)
    tick_candles = np.empty((n_candles, 7), dtype=float)

    for i in range(n_candles):
        bucket = trades[i*bucket_size:(i+1)*bucket_size]

        time = bucket[0, 0]
        open = bucket[0, 2]
        high = np.max(bucket[:, 2])
        low = np.min(bucket[:, 2])
        close = bucket[-1, 2]
        volume = np.sum(bucket[:, 3])
        turnover = np.sum(bucket[:, 3] * bucket[:, 2])

        tick_candles[i, :] = np.array([time, open, high, low, close, volume, turnover])

    return tick_candles


def _combine_trades_arr(arr1: np.ndarray, arr2: np.ndarray) -> np.ndarray:
    combined = np.concatenate((arr1, arr2))
    sorted_trades = combined[combined[:, 0].argsort()]
    return sorted_trades[arr1.shape[0]:]


@njit
def momentum_v1(candles: np.ndarray, lengths: np.ndarray) -> float:
    """
    Make sure lengths are fed in from longest to shortest
    """

    closes = candles[:, 4]
    curr_price = closes[-1]
    n = lengths.size
    vals = np.empty(n, dtype=float)

    for i in range(n):
        length = lengths[i]
        ema_val = ema(closes[-length:], length)[-1]

        # Safety check
        if ema_val == 0:
            vals[i] = vals[i-1]   

        else:
            vals[i] = np.log(curr_price / ema_val) * 100

    trend_val = ema(vals, n)[-1]

    return trend_val


@njit
def momentum_v2(candles: np.ndarray, lengths: np.ndarray) -> float:
    """
    Determines current strength of momentum, normalized output

    Args:
        candles (np.ndarray): Array of [T, O, H, L, C, V, Turnover]
        lengths (np.ndarray): Array of EMA lengths (Longest => Shortest)
    
    Returns:
        float: A normalized value for current momentum

    --------------------------------------------------

    Small explanation of feature:
        > Generates multiple EMAs, and compares current price to them\n
        > The log difference between them, weighted then summed\n
        > Smooth the normalized price\n
        > Subtract current val with smoothed for final value(s)
    """

    closes = candles[-lengths[0]:, 4]
    n_closes = closes.size
    n_lengths = lengths.size
    weights = ema_weights(n_lengths) * 100

    processed_emas = np.empty((n_lengths, n_closes), dtype=float)

    for i in range(n_lengths):
        i_ema = ema(closes, lengths[i])
        logged = np.log(closes / i_ema)
        weighted = logged * weights[i]
        processed_emas[i, :] = weighted

    summed_emas = np.sum(processed_emas, axis=1)
    smoothed = ema(summed_emas, 3)
    trend_filter = ema(smoothed, 20)
    spread = smoothed[-1] - trend_filter[-1]

    return spread

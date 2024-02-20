import numpy as np
from numba import njit
from numpy.typing import NDArray

@njit(cache=True)
def bbw(klines: NDArray, length: int, multiplier: float) -> float:
    """
    Calculates the Bollinger Band Width (BBW) for a given set of klines.

    Parameters
    ----------
    klines : NDArray
        The klines data array, where each row represents a kline and the 5th column contains the close prices.
    length : int
        The number of periods to use for calculating the EMA and the standard deviation.
    multiplier : float
        The multiplier for the standard deviation to calculate the width of the bands.

    Returns
    -------
    float
        The width of the Bollinger Bands for the given parameters.

    Notes
    -----
    - The function assumes that the input `klines` array's 5th column (index 4) contains the closing prices.
    - This implementation is optimized for performance with Numba's JIT compiler.
    """
    closes = klines[:, 4]
    dev = multiplier * np.std(closes[-length:])
    return 2 * dev 
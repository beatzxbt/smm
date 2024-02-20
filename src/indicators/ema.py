import numpy as np
from numba import njit
from numpy.typing import NDArray

@njit(cache=True)
def ema(arr_in: NDArray, window: int) -> NDArray:
    """
    Calculates the Exponential Moving Average (EMA) of an input array.

    Parameters
    ----------
    arr_in : NDArray
        The input array for which the EMA is calculated. Typically, this is an array of closing prices.
    window : int
        The window size for the EMA calculation, specifying the number of periods to consider for the moving average.

    Returns
    -------
    NDArray
        An array of the same length as `arr_in`, containing the calculated EMA values.

    Notes
    -----
    - The first EMA value is simply the first value of `arr_in`, as there's no preceding data to average.
    - This implementation initializes the EMA calculation with the first data point in the input array.
    """
    n = arr_in.size
    ewma = np.empty(n, dtype=np.float64)
    alpha = 2 / (window + 1)
    ewma[0] = arr_in[0]

    for i in range(1, n):
        ewma[i] = (arr_in[i] * alpha) + (ewma[i-1] * (1 - alpha))

    return ewma
import numpy as np
from numba import njit
from numpy.typing import NDArray
from typing import Optional

@njit(cache=True)
def ema(arr_in: NDArray, window: int, alpha: Optional[float]=0) -> NDArray:
    """
    Calculates the Exponential Moving Average (EMA) of an input array.

    Parameters
    ----------
    arr_in : NDArray
        The input array for which the EMA is calculated. Typically, this is an array of closing prices.
    window : int
        The window size for the EMA calculation, specifying the number of periods to consider for the moving average.
    alpha : float, optional
        The decay factor for the EMA calculation. If not provided, it is calculated as 3 / (window + 1).

    Returns
    -------
    NDArray
        An array of the same length as `arr_in`, containing the calculated EMA values.

    Notes
    -----
    - The first EMA value is simply the first value of `arr_in`, as there's no preceding data to average.
    - This implementation initializes the EMA calculation with the first data point in the input array.
    """
    alpha = 3 / float(window + 1) if alpha == 0 else alpha
    n = arr_in.size
    ewma = np.empty(n, dtype=np.float64)
    ewma[0] = arr_in[0]

    for i in range(1, n):
        ewma[i] = (arr_in[i] * alpha) + (ewma[i-1] * (1 - alpha))

    return ewma

@njit
def ema_weights(window: int, reverse: bool=False, alpha: Optional[float]=0) -> NDArray:
    """
    Calculate EMA (Exponential Moving Average)-like weights for a given window size.

    Parameters
    ----------
    window : int
        The number of periods to use for the EMA calculation.
    reverse : bool, optional
        If True, the weights are returned in reverse order. The default is False.
    alpha : float, optional
        The decay factor for the EMA calculation. If not provided, it is calculated as 3 / (window + 1).

    Returns
    -------
    NDArray
        An array of EMA-like weights.

    Examples
    --------
    >>> ema_weights(window=5)
    array([0.33333333, 0.22222222, 0.14814815, 0.09876543, 0.06584362])

    >>> ema_weights(window=5, reverse=True)
    array([0.06584362, 0.09876543, 0.14814815, 0.22222222, 0.33333333])

    >>> ema_weights(window=5, alpha=0.5)
    array([0.5    , 0.25   , 0.125  , 0.0625 , 0.03125])
    """
    alpha = 3 / float(window + 1) if alpha == 0 else alpha
    weights = np.empty(window, dtype=np.float64)

    for i in range(window):
        weights[i] = alpha * (1 - alpha) ** i
 
    return weights[::-1] if reverse else weights
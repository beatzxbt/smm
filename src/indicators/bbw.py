import numpy as np
from numba import njit, prange
from src.indicators.ema import ema


@njit(parallel=True, nogil=True)
def bbw(arr_in: np.array, length: int, std: int) -> np.array:
    """
    Hyper-fast Bollinger Band Width implementation \n
    Be careful with the data type in the array! 
    """

    n = len(arr_in)
    close = np.empty(n, dtype=np.float64)

    for i in prange(n):
        close[i] = arr_in[i][4]

    basis = ema(close, length)
    dev = std * np.std(close[-length:])
    upper = basis[-1] + dev
    lower = basis[-1] - dev
    bbw = np.sqrt(upper-lower)
        
    return bbw
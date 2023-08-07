import numpy as np
from numba import njit, prange
from src.indicators.ema import ema


@njit(parallel=True, fastmath=True)
def bbw(arr_in: np.array, length: int, std: int) -> np.array:
    """
    Hyper-fast Bollinger Band Width implementation \n
    Be careful with the data type in the array! 
    """

    close = arr_in[:, 4] 

    basis = ema(close, length)[-1]
    dev = std * np.std(close[-length:])
    upper = basis + dev
    lower = basis - dev
    bbw = upper - lower

    return bbw
import numpy as np
from numba import njit
from src.indicators.ema import ema

@njit(nogil=True)
def bbw(arr_in: np.array, length: int, std: int) -> np.array:
    """
    Hyper-fast Bollinger Band Width implementation \n
    Be careful with the data type in the array! 
    """
    basis = ema(arr_in, length)
    dev = std * np.std(arr_in[-length:])
    upper = basis[-1] + dev
    lower = basis[-1] - dev
    bbw = np.sqrt(upper-lower)
        
    return bbw
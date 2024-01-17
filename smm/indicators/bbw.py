import numpy as np
from numba import njit

@njit
def bbw(arr_in: np.ndarray, length: int, multiplier: int) -> np.ndarray:
    """Hyper-fast Bollinger Band Width implementation"""
    dev = multiplier * np.std(arr_in[-length:])
    return dev * 2
    
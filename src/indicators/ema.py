import numpy as np
from numba import njit, float64, int64

@njit((float64[:], int64), nogil=True)
def ema(arr_in: np.array, window: int) -> np.array:
    """
    Hyper-fast EMA implementation \n
    Be careful with the data type in the array! 
    """
    n = arr_in.shape[0]
    ewma = np.empty(n, dtype=float64)
    alpha = 2 / float(window + 1)
    w = 1
    ewma_old = arr_in[0]
    ewma[0] = ewma_old

    for i in range(1, n):
        w += (1-alpha)**i
        ewma_old = ewma_old*(1-alpha) + arr_in[i]
        ewma[i] = ewma_old / w
        
    return ewma
import numpy as np
from numba import njit, float64
from numpy.typing import NDArray

@njit(nogil=True)
def ema(arr_in: NDArray, window: int) -> NDArray:
    """Hyper-fast EMA implementation"""
    n = arr_in.size
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
    
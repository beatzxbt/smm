
import numpy as np
from numba import njit


@njit(nogil=True)
def ema(arr_in: np.ndarray, window: int) -> np.ndarray:
    """
    Hyper-fast EMA implementation
    """
    
    n = arr_in.shape[0]
    ewma = np.empty(n, dtype=float)
    alpha = 2 / float(window + 1)
    w = 1
    ewma_old = arr_in[0]
    ewma[0] = ewma_old

    for i in range(1, n):
        w += (1-alpha)**i
        ewma_old = ewma_old*(1-alpha) + arr_in[i]
        ewma[i] = ewma_old / w
        
    return ewma
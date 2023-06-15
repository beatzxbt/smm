import numpy as np
from numba import njit, prange, float64, int64


@njit((float64, int64))
def nsqrt(value: float, n: int) -> float:
    """
    Return the n'th root of a value
    """
    if n == 1:
        return np.sqrt(value)
    
    else:
        for _ in range(n):
            value = np.sqrt(value)

        return value


@njit((float64, float64, int64))
def linspace(start, end, n):
    return np.linspace(start, end, n)





import numpy as np
from numba import njit
from numpy.typing import NDArray

@njit(["float64[:](float64, float64, int64)"])
def nblinspace(start: float, end: float, n: int) -> NDArray:
    return np.linspace(start, end, n)

@njit(["float64[:](float64, float64, int64)"])
def nbgeomspace(start: float, end: float, n: int) -> NDArray:
    return np.geomspace(start, end, n)

@njit(["float64(float64, int64)"])
def nbround(num: float, digit: int) -> float:
    return np.around(num, digit)
    
@njit(["float64(float64, float64, float64)"])
def nbclip(val: float, min: float, max: float) -> float:
    if val < min:
        return min
    elif val > max:
        return max
    else:
        return val
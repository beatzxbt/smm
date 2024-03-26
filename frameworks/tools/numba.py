import numpy as np
from numba import njit, float64, uint8
from numpy.typing import NDArray

@njit(float64[:](float64, float64, uint8), cache=True)
def nblinspace(start: float, end: float, n: int) -> NDArray:
    return np.linspace(start, end, n)

@njit(float64[:](float64, float64, uint8), cache=True)
def nbgeomspace(start: float, end: float, n: int) -> NDArray:
    return np.geomspace(start, end, n)

@njit(float64(float64, uint8), cache=True)
def nbround(num: float, digit: int) -> float:
    return np.around(num, digit)
    
@njit(float64(float64, float64, float64), cache=True)
def nbclip(val: float, min: float, max: float) -> float:
    if val < min:
        return min
    elif val > max:
        return max
    else:
        return val
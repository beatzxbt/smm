import numpy as np
from numba import njit, float64, uint8

@njit(float64[:](float64, float64, uint8))
def nblinspace(start: float, end: float, n: int) -> np.ndarray:
    return np.linspace(start, end, n)

@njit(float64(float64, uint8))
def nbround(num: float, digit: int) -> float:
    return np.around(num, digit)

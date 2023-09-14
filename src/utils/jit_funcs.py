
import numpy as np
from numba import njit, float64, int32

# Using ** for power is often faster with Numba #

@njit(float64(float64, int32))
def nsqrt(value: float, n: int) -> float:
    """
    Return the n'th root of a value
    """

    if n == 1:
        return value**0.5

    else:
        for _ in range(n):
            value = value**0.5

        return value


@njit(float64(float64, int32))
def npower(value: float, n: int) -> float:
    """
    Return the n'th square of a value
    """
    return value**n 


@njit(float64(float64))
def nabs(value: float) -> float:
    """
    Return the absolute of a value
    """
    return np.abs(value)


@njit(float64[:](float64, float64, int32))
def nlinspace(start: float, end: float, n: int) -> np.ndarray:
    return np.linspace(start, end, n)
    
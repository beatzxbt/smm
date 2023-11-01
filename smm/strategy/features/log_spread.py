
import numpy as np
from numba import njit, float64


@njit(float64(float64, float64))
def log_spread(price: float, benchmark: float) -> float:
    """
    Log difference between two prices (*100)
    """

    return np.log(price/benchmark) * 100

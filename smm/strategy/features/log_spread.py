import numpy as np
from numba import njit, float64

@njit(float64(float64, float64), cache=True)
def log_spread(price: float, benchmark: float) -> float:
    """Log difference between a price and a benchmark"""
    return np.log(price/benchmark) * 100
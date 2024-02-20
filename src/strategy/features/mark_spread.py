import numpy as np
from numba import njit

@njit
def log_price_difference(p1: float, p2: float) -> float:
    """
    Log difference between price1 relative to price2
    """
    return np.log(p1/p2) * 100
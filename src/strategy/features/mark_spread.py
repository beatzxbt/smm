
import numpy as np
from numba import njit


@njit
def mark_price_spread(mark_price: float, wmid: float) -> float:
    """
    Difference between mark price and weighted-mid-price
    """

    return np.log(mark_price/wmid) * 100

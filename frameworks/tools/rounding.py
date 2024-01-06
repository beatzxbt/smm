import numpy as np
import numba as nb
from decimal import Decimal

def round_step_size(num: float, step: float) -> float:
    """
    Originally from binance.helpers.round_step_size
    """
    num = Decimal(str(num))
    return float(num - num % Decimal(str(step)))

@nb.njit(nb.float64(nb.float64, nb.float64))
def round_step_size_fast(num: float, step: float) -> float:
    p = int(1/step)
    return np.floor(num*p)/p

import numpy as np
from numba import njit, float64

@njit(float64(float64, float64), cache=True)
def round_step(num: float, step: float) -> float:
    p = int(1/step)
    return np.floor(num*p)/p

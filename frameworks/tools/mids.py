
import numpy as np
from numba import njit, float64


@njit(float64(float64[:]), cache=True)
def calculate_mid_price(bba: np.ndarray) -> float:
    return (bba[1][0] + bba[0][0])/2


@njit(float64(float64[:]), cache=True)
def calculate_weighted_mid_price(bba: np.ndarray) -> float:
    imb = bba[0][1] / (bba[0][1] + bba[1][1])
    return bba[1][0] * imb + bba[0][0] * (1 - imb)

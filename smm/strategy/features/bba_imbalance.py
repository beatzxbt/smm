from numpy.typing import NDArray
from numba import njit, float64

@njit(float64(float64[:]), cache=True)
def bba_imbalance(bba: NDArray) -> float:
    """Imbalance between bid and ask quantities"""
    return ((bba[0][1]/(bba[1][1] + bba[0][1])) - 0.5) * 2

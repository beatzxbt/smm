
from numba import njit


@njit
def bba_imbalance(bid: float, ask: float) -> float:
    """
    Imbalance between bid and ask quantities
    """

    return ((bid/(ask + bid)) - 0.5) * 2

import numpy as np
from numba import njit
from numba.types import float64, Array


@njit(error_model="numpy", fastmath=True)
def generate_geometric_weights(
    num: int, r: float = 0.75, reverse: bool = True
) -> Array:
    """
    Generates a list of `num` weights that follow a geometric distribution and sum to 1.

    Parameters
    ----------
    num : int
        The number of weights to generate.

    r : float, optional
        The common ratio of the geometric sequence. Must be strictly between 0 and 1. The default value is 0.75.

    reverse : bool, optional
        If True, the weights will be generated in reverse order. If False, the weights will be generated in ascending order.
        The default is True.

    Returns
    -------
    Array
        An array of weights, following a geometric distribution, whose sum is 1.
    """
    weights = np.array([r**i for i in range(num)], dtype=float64)
    normalized = weights / weights.sum()
    return normalized[::-1] if reverse else normalized

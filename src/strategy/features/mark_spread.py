import numpy as np
from numba import njit

@njit(cache=True)
def log_price_difference(follow: float, base: float) -> float:
    """
    Calculates the logarithmic price difference between two prices, scaled by 100.

    Parameters
    ----------
    follow : float
        The price you intend on following (eg., price from the most liquid venue).
    base : float
        The price you are comparing it to (eg., price from the venue you're trading).

    Returns
    -------
    float
        The logarithmic difference between the two prices, scaled by 100.
        A positive value indicates that follow price is higher than base price, while a
        negative value indicates that follow price is lower than base price.

    Examples
    --------
    >>> log_price_difference(follow=49000, base=48980)
    0.04082465866049452

    >>> log_price_difference(follow=48980, base=49000)
    -0.04082465866049452
    """
    return np.log(base / follow) * 100
from numpy.typing import NDArray

def bba_imbalance(bba: NDArray) -> float:
    """
    Calculates the imbalance between bid and ask quantities.

    Parameters
    ----------
    bba : NDArray
        An array containing the best bid and ask quantities, in the format 
        [[bid price, bid size], [ask price, ask size]].

    Returns
    -------
    float
        The normalized imbalance between bid and ask quantities. The value ranges from -1 to 1.
    """
    return ((bba[0, 1] / (bba[1, 1] + bba[0, 1])) - 0.5) * 2
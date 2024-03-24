from numba import njit, float64

@njit(float64(float64, float64), cache=True)
def round_num(num: float, step: float) -> float:
    """
    Rounds a float to a given step size
    """
    p = round(1/step)
    return round(num*p)/p
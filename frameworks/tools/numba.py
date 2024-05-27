import numpy as np
from numba import njit
from numba.types import Array, bool_
from numpy.typing import NDArray


@njit(["float64[:](float64, float64, int64)"])
def nblinspace(start: float, end: float, n: int) -> NDArray:
    return np.linspace(start, end, n)


@njit(["float64[:](float64, float64, int64)"])
def nbgeomspace(start: float, end: float, n: int) -> NDArray:
    return np.geomspace(start, end, n)


@njit(["float64(float64, int64)"])
def nbround(num: float, digit: int) -> float:
    return np.around(num, digit)


@njit(["float64(float64, float64, float64)"])
def nbclip(val: float, min: float, max: float) -> float:
    if val < min:
        return min
    elif val > max:
        return max
    else:
        return val
    

@njit(fastmath=True)
def nbdiff_1d(a: Array, n: int=1) -> Array:
    """
    Compute the n-th discrete difference along the given axis for 1D arrays.

    Parameters
    ----------
    a : Array
        Input array of any shape.

    n : int, optional
        The number of times values are differenced. If zero, the input is returned as-is.
        Default is 1.

    Returns
    -------
    Array
        The n-th differences. The shape of the output is the same as `a` except along the 
        given axis. The length of the shape along that axis is `max(a.shape[axis] - n, 0)`.
    """
    if n == 0:
        return a.copy()
    
    if n < 0:
        raise ValueError("diff(): order must be non-negative")
    
    a_size = a.size
    out_size = max(a_size - n, 0)
    out = np.empty(out_size, dtype=a.dtype)
    
    if out_size == 0:
        return out
    
    work = np.empty_like(a)
    
    # First iteration: diff a into work
    for i in range(a_size - 1):
        work[i] = a[i + 1] - a[i]
    
    # Other iterations: diff work into itself
    for niter in range(1, n):
        for i in range(a_size - niter - 1):
            work[i] = work[i + 1] - work[i]
    
    # Copy final diff into out
    out[:] = work[:out_size]

    return out

@njit(fastmath=True)
def nbisin(a: Array, b: Array) -> Array:
    out = np.empty(a.size, dtype=bool_)
    b = set(b)

    for i in range(a.size):
        out[i] = True if a[i] in b else False

    return out

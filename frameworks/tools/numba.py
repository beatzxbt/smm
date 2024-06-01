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
def nbdiff_1d(a: Array, n: int = 1) -> Array:
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


# ---------------------------------------- #
# Copied from: https://gist.github.com/DannyWeitekamp/7b07d7854497f073ab860e35db7ece81
# Only modifications are for code cleanliness and removing excessive imports
# Usecase: Printing floats in jitclasses (eg. Orderbook.display() func)

from numba.cpython.unicode import _empty_string, _set_code_point, PY_UNICODE_1BYTE_KIND


@njit(cache=True)
def _get_n_digits_(x):
    l1, l2 = 0, -1
    _x = x
    while _x > 0:
        _x = _x // 10
        l1 += 1

    _x = x % 10
    while _x > 1e-10:
        _x = (_x * 10) % 10
        l2 += 1
        if l2 >= 16:
            break
    return l1, l2


@njit
def nb_float_to_str(x: float) -> str:
    """
    Converts a floating-point number to its string representation with exponential notation if necessary.

    This function handles special cases such as infinity and negative infinity, and can format
    the number using exponential notation if the exponent is large (greater than or equal to 16)
    or very small (less than or equal to -16). The result is a string representation of the number
    with up to 15 decimal places of precision.

    Parameters
    ----------
    x : float
        The floating-point number to be converted to a string.

    Returns
    -------
    str
        The string representation of the input floating-point number.

    Notes
    -----
    - If the input number is positive or negative infinity, the function returns 'inf' or '-inf' respectively.
    - For large exponents (>= 16) or small exponents (<= -16), the number is converted using exponential notation.
    - The function can handle up to 15 decimal places of precision.

    Examples
    --------
    >>> nb_float_to_str(123456789.123456789)
    '1.23456789123457e+08'

    >>> nb_float_to_str(-0.000000123456789)
    '-1.23456789000000e-07'

    >>> nb_float_to_str(np.inf)
    'inf'

    >>> nb_float_to_str(-np.inf)
    '-inf'
    """
    DIGITS_START = 48
    DASH = 45
    DOT = 46
    PLUS = 43
    E_CHAR = 101

    if x == np.inf:
        return "inf"
    elif x == -np.inf:
        return "-inf"

    isneg = int(x < 0.0)
    x = np.abs(x)

    if x != 0.0:
        # There is probably a more efficient way to do this
        e = np.floor(np.log10(x))
        if 10**e - x > 0:
            e -= 1
    else:
        e = 0

    is_exp, is_neg_exp = e >= 16, e <= -16

    exp_chars = 0
    if is_exp or is_neg_exp:
        exp_chars = 4
        if e >= 100 or e <= -100:
            exp_chars = 5

    if is_exp:
        offset_x = np.around(x * (10.0 ** -(e)), 15)
        l1, l2 = _get_n_digits_(offset_x)
    elif is_neg_exp:
        offset_x = np.around(x * (10 ** -(e)), 15)
        l1, l2 = _get_n_digits_(offset_x)
    else:
        offset_x = x
        l1, l2 = _get_n_digits_(x)
        l2 = max(1, l2)  # Will have at least .0

    use_dec = l2 > 0

    # print("<<", e, offset_x, l2)

    l = l1 + l2 + use_dec
    length = l + isneg + exp_chars
    s = _empty_string(PY_UNICODE_1BYTE_KIND, length)
    if isneg:
        _set_code_point(s, 0, DASH)

    _x = offset_x
    for i in range(l1):
        digit = int(_x % 10)
        _set_code_point(s, (isneg + l1) - i - 1, digit + DIGITS_START)
        _x = _x // 10

    if use_dec:
        _set_code_point(s, l1 + isneg, DOT)

    _x = offset_x % 10
    for i in range(l2):
        _x = (_x * 10) % 10
        digit = int(_x)

        _set_code_point(s, (isneg + l1) + i + use_dec, digit + DIGITS_START)

    if is_exp or is_neg_exp:
        i = isneg + l1 + use_dec + l2
        _set_code_point(s, i, E_CHAR)
        if is_exp:
            _set_code_point(s, i + 1, PLUS)
        if is_neg_exp:
            _set_code_point(s, i + 1, DASH)

        i = length - 1
        exp = np.abs(e)
        while exp > 0:
            digit = exp % 10
            _set_code_point(s, i, digit + DIGITS_START)
            exp = exp // 10
            i -= 1

    return s

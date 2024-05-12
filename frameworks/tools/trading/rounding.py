import numpy as np
from numba import njit
from numba.types import Array
from typing import Union


@njit(error_model="numpy", cache=True)
def round_ceil(
    num: Union[float, Array], step_size: Union[float, int]
) -> Union[float, int]:
    """
    Rounds a number or array of numbers up to the nearest multiple of a given step size.

    Parameters
    ----------
    num : Union[float, Array]
        The number or array of numbers to be rounded.

    step_size : Union[float, int]
        The step size to round up to the nearest multiple of.

    Returns
    -------
    Union[float, int]
        The rounded number or array of numbers.

    Examples
    --------
    >>> round_ceil(5.1, 0.5)
    5.5
    >>> round_ceil(np.array([2.3, 4.6, 6.1]), 2)
    np.array([4, 6, 8])
    """
    return np.round(
        step_size * np.ceil(num / step_size), int(np.ceil(-np.log10(step_size)))
    )


@njit(error_model="numpy", cache=True)
def round_floor(
    num: Union[float, Array], step_size: Union[float, int]
) -> Union[float, int]:
    """
    Rounds a number or array of numbers down to the nearest multiple of a given step size.

    Parameters
    ----------
    num : Union[float, Array]
        The number or array of numbers to be rounded.

    step_size : Union[float, int]
        The step size to round down to the nearest multiple of.

    Returns
    -------
    Union[float, int]
        The rounded number or array of numbers.

    Examples
    --------
    >>> round_floor(5.8, 0.5)
    5.5
    >>> round_floor(np.array([2.7, 4.2, 6.9]), 2)
    np.array([2, 4, 6])
    """
    return np.round(
        step_size * np.floor(num / step_size), int(np.ceil(-np.log10(step_size)))
    )


@njit(error_model="numpy", cache=True)
def round_discrete(
    num: Union[float, Array], step_size: Union[float, int]
) -> Union[float, int]:
    """
    Rounds a number or array of numbers to the nearest multiple of a given step size.

    Parameters
    ----------
    num : Union[float, Array]
        The number or array of numbers to be rounded.

    step_size : Union[float, int]
        The step size to round to the nearest multiple of.

    Returns
    -------
    Union[float, int]
        The rounded number or array of numbers.

    Examples
    --------
    >>> round_discrete(5.3, 0.5)
    5.5
    >>> round_discrete(np.array([2.4, 4.5, 7.7]), 2)
    np.array([2., 4., 8.])
    """
    return np.round(
        step_size * np.round(num / step_size), int(np.ceil(-np.log10(step_size)))
    )

import numpy as np
from numba import njit
from numpy_ringbuffer import RingBuffer
from numpy.typing import NDArray
from typing import Optional


class EMA:
    """
    A class representing the Exponential Moving Average (EMA) calculation for a dataset.

    Attributes
    ----------
    window : int
        The window size for the EMA calculation.

    alpha : float
        The smoothing factor for the EMA. If set to 0, it is calculated as 2 / (window + 1).

    arr : RingBuffer
        A ring buffer to store EMA values.

    value : float
        The current EMA value.
    """

    def __init__(self, window: int, alpha: Optional[float]=0) -> None:
        """
        Initializes the EMA instance with a specified window size and alpha.

        Parameters
        ----------
        window : int
            The window size for the EMA calculation.

        alpha : float, optional
            The smoothing factor. If 0, it is calculated based on the window size.
        """
        self.window = window
        self.alpha = 2 / float(window + 1) if alpha == 0 else alpha
        self.arr = None
        self.value = 0.0

    @property
    def __value__(self) -> float:
        """Returns the latest value of the EMA."""
        return self.value

    @property
    def __arr__(self) -> NDArray:
        """Unwraps and returns the internal ring buffer as an NDArray."""
        return self.arr._unwrap()

    def initialize(self, arr_in: NDArray) -> None:
        """
        Initializes the EMA calculation with a given array of input values.

        Parameters
        ----------
        arr_in : NDArray
            An array of input values to initialize the EMA calculation.
        """
        self.arr = RingBuffer(arr_in.size, dtype=np.float64)
        for val in _ema_(arr_in, self.alpha):
            self.arr.append(val)
        self.value = self.arr[-1]

    def update(self, new_val: float) -> None:
        """
        Updates the EMA calculation with a new incoming value.

        Parameters
        ----------
        new_val : float
            The new value to include in the EMA calculation.
        """
        updated_value = _recursive_ema_(self.value, new_val, self.alpha)
        self.arr.append(updated_value)
        self.value = updated_value


@njit(cache=True)
def _ema_(arr_in: NDArray, alpha: float) -> NDArray:
    """
    Calculates the EMA for an array of input values.

    The EMA is calculated using the following steps:
    1. Initialize an empty array for the EMA values.
    2. Set the first value of the EMA array to the first value of the input array.
    3. For each subsequent value in the input array:
       a. Apply the EMA formula: EMA_old = EMA_old * (1 - alpha) + new_value.
       b. Divide the updated EMA_old by the cumulative weight for the current position.
       c. Store this value in the corresponding position in the EMA array.

    Parameters
    ----------
    arr_in : NDArray
        The input array for which to calculate the EMA.
        
    alpha : float
        The smoothing factor for the EMA.

    Returns
    -------
    NDArray
        An array of EMA values.
    """
    len_arr_in = arr_in.size
    ewma = np.empty(len_arr_in, dtype=np.float64)
    w = 1
    ewma_old = arr_in[0]
    ewma[0] = ewma_old

    for i in range(1, len_arr_in):
        w += (1 - alpha) ** i
        ewma_old = ewma_old * (1 - alpha) + arr_in[i]
        ewma[i] = ewma_old / w

    return ewma


@njit(cache=True)
def _recursive_ema_(ema_val: float, update: float, alpha: float) -> float:
    """
    Recursively updates the EMA value with a new data point.

    Parameters
    ----------
    ema_val : float
        The current EMA value.

    update : float
        The new data point to update the EMA.

    alpha : float
        The smoothing factor for the EMA.

    Returns
    -------
    float
        The updated EMA value.
    """
    return alpha * update + (1 - alpha) * ema_val

import numpy as np
from numba import njit
from numpy.typing import NDArray
from numpy_ringbuffer import RingBuffer


class EMA:
    def __init__(self, window: int, alpha: float = 0) -> None:
        self.window = window
        self.alpha = 2 / float(window + 1) if alpha == 0 else alpha
        self._arr_ = None
        self.value = 0.0

    @property
    def __value__(self) -> float:
        return self.value

    def __arr__(self) -> NDArray:
        return self._arr_._unwrap()

    def initialize(self, arr_in: NDArray) -> NDArray:
        self._arr_ = RingBuffer(arr_in.size, dtype=np.float64)
        for val in _ema_(arr_in, self.alpha):
            self._arr_.append(val)
        self.value = self._arr_[-1]

    def update(self, new_val):
        updated_value = _recursive_ema_(new_val, self.alpha)
        self._arr_.append(updated_value)
        self.value = updated_value


@njit(cache=True)
def _ema_(arr_in: NDArray, alpha: float) -> NDArray:
    """EMA go brrr"""
    n = arr_in.size
    ewma = np.empty(n, dtype=np.float64)
    w = 1
    ewma_old = arr_in[0]
    ewma[0] = ewma_old

    for i in range(1, n):
        w += (1 - alpha) ** i
        ewma_old = ewma_old * (1 - alpha) + arr_in[i]
        ewma[i] = ewma_old / w

    return ewma


@njit(cache=True)
def _recursive_ema_(ema_val: float, update: float, alpha: int) -> NDArray:
    return alpha * update + (1 - alpha) * ema_val

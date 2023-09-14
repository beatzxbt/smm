
import numpy as np
from numba import njit
from src.indicators.ema import ema


@njit
def bbw(klines: np.ndarray, length: int, multiplier: int) -> np.ndarray:
    """
    Hyper-fast Bollinger Band Width implementation
    """

    closes = klines[:, 4] 
    basis = ema(closes, length)[-1]
    dev = multiplier * np.std(closes[-length:])
    upper = basis + dev
    lower = basis - dev
    bbw = upper - lower

    return bbw
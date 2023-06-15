import numpy as np
from numba import njit, prange
from src.utils.jit_funcs import nsqrt


@njit(parallel=True, fastmath=True)
def simple_range(arr_in: np.array, lookback: int, norm_passes: int):
    """
    Provides a simple volatility measure to define a base range
    {arr_in}: an array of (high: float64, low: float64) 
    {lookback}: the past period of differences it adds up
    {norm_passes}: number of np.sqrt() iters to normalize the value
    """
    
    arr_in = arr_in[-lookback:]
    diff = np.empty(lookback, dtype=np.float64)

    for i in prange(lookback):
        high = arr_in[i][0]
        low = arr_in[i][1]
        diff[i] = np.abs(high-low)

    diff_sum = np.sum(diff)
    
    if norm_passes == 0:
        return diff_sum
    
    else:
        diff_sum = nsqrt(diff_sum, norm_passes)
        
        return diff_sum
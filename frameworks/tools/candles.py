import numpy as np
from numba import njit, prange
from numpy.typing import NDArray
from numpy_ringbuffer import RingBuffer


class TickCandles:
    def __init__(self, trades: RingBuffer, bucket_size: int):
        self.trades = trades # NOTE: Pointer to appropriate RingBuffer in ss.market{}
        self.bucket_size = bucket_size
    
        self.tickbars = RingBuffer(trades, dtype=(float, 6)) # OHLCV

    def _update_(self) -> RingBuffer:
        "Interal func, update tick bars with new trades"
        pass
    
    def fetch(self) -> NDArray:
        "Return tick bars as an NDArray"
        return self.tickbars._unwrap()


class VolumeCandles:
    def __init__(self, trades: RingBuffer, bucket_size: int):
        self.trades = trades # NOTE: Pointer to appropriate RingBuffer in ss.market{}
        self.bucket_size = bucket_size
    
        self.volumebars = RingBuffer(trades, dtype=(float, 6)) # OHLCV

    def _update_(self) -> RingBuffer:
        "Interal func, update volume bars with new trades"
        pass
    
    def fetch(self) -> NDArray:
        "Return volume bars as an NDArray"
        return self.volumebars._unwrap()


@njit(parallel=True, cache=True)
def _generate_tick_candles_(trades: NDArray, bucket_size: int) -> NDArray:
    num_candles = int(trades.shape[0]/bucket_size)
    tick_candles = np.empty((num_candles, 6), dtype=float)

    for i in prange(num_candles):
        bucket = trades[i*bucket_size : (i+1)*bucket_size]
        tick_candles[i, :] = np.array([
            bucket[0, 0],           # Time
            bucket[0, 2],           # Open
            np.max(bucket[:, 2]),   # High
            np.min(bucket[:, 2]),   # Low
            bucket[-1, 2],          # Close
            np.sum(bucket[:, 3])    # Volume
        ])

    return tick_candles


@njit(cache=True)
def _generate_volume_candles_(trades: NDArray, bucket_size: int) -> NDArray:
    num_trades = trades.shape[0]
    volume_candles = np.empty((num_trades, 6), dtype=float)
    num_candles = 0

    vol = 0
    idx = 0
    previous_idx = 0

    while idx < num_trades: 
        vol += trades[idx][3]

        if vol >= bucket_size:
            bucket = trades[previous_idx : idx]
            volume_candles[num_candles, :] = np.array([
                bucket[0, 0],           # Time
                bucket[0, 2],           # Open
                np.max(bucket[:, 2]),   # High
                np.min(bucket[:, 2]),   # Low
                bucket[-1, 2],          # Close
                np.sum(bucket[:, 3])    # Volume
            ])

            vol = 0
            previous_idx = idx
            num_candles += 1

    return volume_candles[:num_candles]
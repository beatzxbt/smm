import numpy as np
from numba import njit, float64, int64, bool_
from numpy.typing import NDArray

@njit(cache=True)
def exponential_weights(window: int, reverse: bool=True) -> NDArray:
    alpha = 2 / float(window + 1)
    weights = np.empty(window, dtype=float64)
    for i in range(window):
        weights[i] = alpha * (1 - alpha) ** i
    return weights[::-1] if reverse else weights

@njit(cache=True)
def mid(bba: NDArray) -> float:
    return (bba[1][0] + bba[0][0])/2

@njit(cache=True)
def wmid(bba: NDArray) -> float:
    imb = bba[0][1] / (bba[0][1] + bba[1][1])
    return bba[1][0] * imb + bba[0][0] * (1 - imb)

@njit(cache=True)
def vamp(asks: NDArray, bids: NDArray, depth: int) -> float:
    bids_qty_sum = np.sum(bids[:depth, 1])
    asks_qty_sum = np.sum(asks[:depth, 1])
    bid_fair = np.sum(bids[:depth, 0] * (bids[:depth, 1] / bids_qty_sum))
    ask_fair = np.sum(asks[:depth, 0] * (asks[:depth, 1] / asks_qty_sum))
    return (ask_fair + bid_fair)/2

@njit(cache=True)
def vamp_weighted(asks: NDArray, bids: NDArray, depth: int) -> float:
    weights = exponential_weights(depth) # TODO: Cache this if possible
    fair_prices = np.empty(depth, dtype=float64)
    bids_cum_qty_sum = np.cumsum(bids[:depth, 1])
    asks_cum_qty_sum = np.cumsum(asks[:depth, 1])

    for i in range(depth):
        bid_fair = np.sum(bids[:i+1, 0] * (bids[:i+1, 1] / bids_cum_qty_sum[i]))
        ask_fair = np.sum(asks[:i+1, 0] * (asks[:i+1, 1] / asks_cum_qty_sum[i]))
        fair_prices[i] = (ask_fair + bid_fair) / 2

    return np.sum(fair_prices * weights) / np.sum(weights)

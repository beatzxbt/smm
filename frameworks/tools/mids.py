import numpy as np
from numba import njit, float64, int64, bool_
from numpy.typing import NDArray
from frameworks.exchange.base.structures.orderbook import Orderbook

@njit(cache=True)
def exponential_weights(window: int, reverse: bool=True) -> NDArray:
    alpha = 2 / float(window + 1)
    weights = np.empty(window, dtype=float64)
    for i in range(window):
        weights[i] = alpha * (1 - alpha) ** i
    return weights[::-1] if reverse else weights

def mid(orderbook: Orderbook) -> float:
    return (orderbook.bba[1, 0] + orderbook.bba[0, 0])/2

def wmid(orderbook: Orderbook) -> float:
    imb = orderbook.bba[0, 1] / (orderbook.bba[0, 1] + orderbook.bba[1, 1])
    return orderbook.bba[1, 0] * imb + orderbook.bba[0, 0] * (1 - imb)

def vamp(orderbook: Orderbook, depth: float) -> float:
    bid_cum_size = np.cumsum(orderbook.bids[:, 1])
    bid_levels_till_depth = bid_cum_size[bid_cum_size <= depth].size
    bid_fair = np.sum(np.prod(orderbook.bids[:bid_levels_till_depth], axis=1) / depth)

    ask_cum_size = np.cumsum(orderbook.asks[:, 1])
    ask_levels_till_depth = ask_cum_size[ask_cum_size <= depth].size
    ask_fair = np.sum(np.prod(orderbook.asks[:ask_levels_till_depth], axis=1) / depth)

    return (bid_fair + ask_fair) / 2

@njit(cache=True)
def weighted_vamp(orderbook: Orderbook, depth: int) -> float:
    weights = exponential_weights(depth)
    fair_prices = np.empty(depth, dtype=float64)
    bids_cum_qty_sum = np.cumsum(orderbook.bids[:depth, 1])
    asks_cum_qty_sum = np.cumsum(orderbook.asks[:depth, 1])

    for i in range(depth):
        bid_fair = np.sum(orderbook.bids[:i+1, 0] * (orderbook.bids[:i+1, 1] / bids_cum_qty_sum[i]))
        ask_fair = np.sum(orderbook.asks[:i+1, 0] * (orderbook.asks[:i+1, 1] / asks_cum_qty_sum[i]))
        fair_prices[i] = (ask_fair + bid_fair) / 2

    return np.sum(fair_prices * weights) / np.sum(weights)

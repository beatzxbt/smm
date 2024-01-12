
import numpy as np
from frameworks.exchange.common.orderbook import BaseOrderBook
from frameworks.sharedstate.market import MarketDataSharedState


class OrderBookBybit(BaseOrderBook):

    def initialize(self, asks, bids):
        self.asks = np.array(asks, float)
        self.bids = np.array(bids, float)
        self.sort_book()


    def update(self, recv):
        asks = np.array(recv["data"]["a"], dtype=float)
        bids = np.array(recv["data"]["b"], dtype=float)

        if recv["type"] == "snapshot":
            self.initialize(asks, bids)

        elif recv["type"] == "delta":
            self.asks = self.update_book(self.asks, asks)
            self.bids = self.update_book(self.bids, bids)

            self.sort_book()

class BybitBBAHandler:


    def __init__(self, sharedstate: MarketDataSharedState, symbol: str) -> None:
        self.bybit = sharedstate.bybit[symbol]


    def update(self, recv):
        best_bid = recv["data"]["b"]
        best_ask = recv["data"]["a"]
        if len(best_bid) != 0:
            price = float(best_bid[0][0])
            qty = float(best_bid[0][1])

            # 0 qty causing div by zero on mid calculations
            if qty > 0:
                self.bybit["bba"][0, 0] = price
                self.bybit["bba"][0, 1] = qty

        if len(best_ask) != 0:
            price = float(best_ask[0][0])
            qty = float(best_ask[0][1])

            # 0 qty causing div by zero on mid calculations
            if qty > 0:
                self.bybit["bba"][1, 0] = price
                self.bybit["bba"][1, 1] = qty

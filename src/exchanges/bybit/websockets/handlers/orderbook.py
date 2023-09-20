
import numpy as np

from src.exchanges.common.localorderbook import BaseOrderBook


class OrderBookBybit(BaseOrderBook):


    def process_snapshot(self, asks, bids):
        self.asks = np.array(asks, float)
        self.bids = np.array(bids, float)
        self.sort_book()


    def process(self, recv):
        asks = np.array(recv["data"]["a"], dtype=float)
        bids = np.array(recv["data"]["b"], dtype=float)

        if recv["type"] == "snapshot":
            self.process_snapshot(asks, bids)

        elif recv["type"] == "delta":
            self.asks = self.update_book(self.asks, asks)
            self.bids = self.update_book(self.bids, bids)

            self.sort_book()



class BybitBBAHandler:


    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate


    def process(self, recv):
        data = recv["data"]
        best_bid = data["b"]
        best_ask = data["a"]

        if len(best_bid) != 0:
            price = float(best_bid[0][0])
            qty = float(best_bid[0][1])

            # 0 qty causing div by 0 on mid calculations)
            if qty > 0:
                self.ss.bybit_bba[0, 0] = price
                self.ss.bybit_bba[0, 1] = qty

        if len(best_ask) != 0:
            price = float(best_ask[0][0])
            qty = float(best_ask[0][1])

            # 0 qty causing div by 0 on mid calculations)
            if qty > 0:
                self.ss.bybit_bba[1, 0] = price
                self.ss.bybit_bba[1, 1] = qty

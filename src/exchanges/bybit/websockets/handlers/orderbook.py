
import numpy as np

from src.exchanges.common.localorderbook import BaseOrderBook


class OrderBookBybit(BaseOrderBook):


    def process_snapshot(self, asks, bids):
        self.asks = np.array(asks, float)
        self.bids = np.array(bids, float)
        self.sort_book()


    def process_data(self, recv):
        asks = np.array(recv['data']['a'], dtype=float)
        bids = np.array(recv['data']['b'], dtype=float)

        if recv["type"] == "snapshot":
            self.process_snapshot(asks, bids)

        elif recv["type"] == "delta":
            self.asks = self.update_book(self.asks, asks)
            self.bids = self.update_book(self.bids, bids)

            self.sort_book()



class BybitBBAHandler:


    def __init__(self, sharedstate, data) -> None:
        self.ss = sharedstate
        self.data = data

    
    def process(self):

        best_bid = self.data['b']
        best_ask = self.data['a']

        if len(best_bid) != 0:
            bb_price = best_bid[0][0]
            bb_qty = best_bid[0][1]
            self.ss.bybit_bba[0] = np.array([bb_price, bb_qty], dtype=float)
            
        if len(best_ask) != 0:
            ba_price = best_ask[0][0]
            ba_qty = best_ask[0][1]
            self.ss.bybit_bba[1] = np.array([ba_price, ba_qty], dtype=float)


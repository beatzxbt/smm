import json
import numpy as np


class LocalOrderBook:


    def __init__(self):
        self.asks = np.empty((0, 2), float)
        self.bids = np.empty((0, 2), float)


    def process_snapshot(self, asks, bids):
        self.asks = np.array(asks, float)
        self.bids = np.array(bids, float)
        self.sort_book()


    def process_update(self, asks, bids):

        for price, qty in asks:
            self.asks = self.asks[self.asks[:, 0] != price]  

            if qty > 0:
                self.asks = np.vstack((self.asks, np.array([price, qty]))) 

        for price, qty in bids: 
            self.bids = self.bids[self.bids[:, 0] != price]  

            if qty > 0:
                self.bids = np.vstack((self.bids, np.array([price, qty]))) 

        self.sort_book()


    def sort_book(self):
        self.asks = self.asks[self.asks[:, 0].argsort()]
        self.bids = self.bids[self.bids[:, 0].argsort()[::-1]]


    def process_data(self, recv):
        
        asks = np.array(recv['data']['a'], dtype=float)
        bids = np.array(recv['data']['b'], dtype=float)

        if recv["type"] == "snapshot":
            self.process_snapshot(asks, bids)

        elif recv["type"] == "delta":
            self.process_update(asks, bids)



class BybitBBAHandler:


    def __init__(self, sharedstate, data: json) -> None:
        self.ss = sharedstate
        self.data = data

    
    def process(self):

        best_bid = self.data['b']
        best_ask = self.data['a']

        if len(best_bid) != 0:
            bb_price = float(best_bid[0][0])
            bb_qty = float(best_bid[0][1])
            self.ss.bybit_bba[0] = np.array([bb_price, bb_qty])
            
        if len(best_ask) != 0:
            ba_price = float(best_ask[0][0])
            ba_qty = float(best_ask[0][1])
            self.ss.bybit_bba[1] = np.array([ba_price, ba_qty])


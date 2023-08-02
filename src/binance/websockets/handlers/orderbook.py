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



class BinanceBBAHandler:


    def __init__(self, sharedstate, recv: json) -> None:
        self.ss = sharedstate
        self.data = recv['data']

    
    def process(self):
        """
        Realtime BBA updates
        """

        bb_price = float(self.data['b'])
        ba_price = float(self.data['a'])

        bb_qty = float(self.data['B'])
        ba_qty = float(self.data['A'])

        self.ss.binance_bba = np.array([[bb_price, bb_qty], [ba_price, ba_qty]])

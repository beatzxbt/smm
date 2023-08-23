
import numpy as np
from src.exchanges.common.localorderbook import BaseOrderBook


class OrderBookBinance(BaseOrderBook):


    def process_snapshot(self, snapshot):
        self.asks = np.array(snapshot['asks'], dtype=float)
        self.bids = np.array(snapshot['bids'], dtype=float)

        self.sort_book()


    def process_data(self, recv):
        recv_data = recv['data']

        asks = np.array(recv_data['a'], dtype=float)
        bids = np.array(recv_data['b'], dtype=float)

        self.asks = self.update_book(self.asks, asks)
        self.bids = self.update_book(self.bids, bids)

        self.sort_book()
            


class BinanceBBAHandler:


    def __init__(self, sharedstate, recv) -> None:
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

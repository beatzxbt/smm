
import numpy as np
from frameworks.exchange.common.localorderbook import BaseOrderBook


class OrderBookBinance(BaseOrderBook):


    def snapshot(self, snapshot: dict):
        self.asks = np.array(snapshot["asks"], dtype=float)
        self.bids = np.array(snapshot["bids"], dtype=float)
        self.sort_book()


    def update(self, recv: dict):
        asks = np.array(recv["data"]["a"], dtype=float)
        bids = np.array(recv["data"]["b"], dtype=float)

        self.asks = self.update_book(self.asks, asks)
        self.bids = self.update_book(self.bids, bids)
        self.sort_book()



class BinanceBBAHandler:


    def __init__(self, sharedstate) -> None:
        self.mdss = sharedstate


    def update(self, recv: dict) -> None:
        """
        Realtime BBA updates
        """
        
        self.mdss.binance["bba"][0, 0] = float(recv["data"]["b"])
        self.mdss.binance["bba"][0, 1] = float(recv["data"]["B"])

        self.mdss.binance["bba"][1, 0] = float(recv["data"]["a"])
        self.mdss.binance["bba"][1, 1] = float(recv["data"]["A"])

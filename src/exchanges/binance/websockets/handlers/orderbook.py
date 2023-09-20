
import numpy as np
from src.exchanges.common.localorderbook import BaseOrderBook


class OrderBookBinance(BaseOrderBook):


    def process_snapshot(self, snapshot: dict):
        self.asks = np.array(snapshot["asks"], dtype=float)
        self.bids = np.array(snapshot["bids"], dtype=float)
        self.sort_book()


    def process(self, recv: dict):
        data = recv["data"]
        asks = np.array(data["a"], dtype=float)
        bids = np.array(data["b"], dtype=float)

        self.asks = self.update_book(self.asks, asks)
        self.bids = self.update_book(self.bids, bids)
        self.sort_book()



class BinanceBBAHandler:


    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate


    def process(self, recv: dict):
        """
        Realtime BBA updates
        """

        data = recv["data"]
        
        self.ss.binance_bba = np.array(
            [[data["b"], data["B"]], [data["a"], data["A"]]],
            dtype=float,
        )

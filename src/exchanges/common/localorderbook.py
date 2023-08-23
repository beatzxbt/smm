
import numpy as np


class BaseOrderBook:


    def __init__(self):
        self.asks = np.empty((0, 2), float)
        self.bids = np.empty((0, 2), float)


    def sort_book(self):
        self.asks = self.asks[self.asks[:, 0].argsort()]
        self.bids = self.bids[self.bids[:, 0].argsort()[::-1]]


    def update_book(self, asks_or_bids, data):

        for price, qty in data:
            asks_or_bids = asks_or_bids[asks_or_bids[:, 0] != price]

            if qty > 0:
                asks_or_bids = np.vstack((asks_or_bids, np.array([price, qty])))

        return asks_or_bids


    def process_data(self, recv):
        raise NotImplementedError("Derived classes should implement this method")
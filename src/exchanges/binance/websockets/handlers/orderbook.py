import numpy as np
from typing import Dict
from src.exchanges.common.localorderbook import BaseOrderBook

class OrderBookBinance(BaseOrderBook):
    """
    Represents the order book for Binance, handling snapshot and real-time updates.

    Inherits from BaseOrderBook to implement Binance-specific order book processing.
    """

    def process_snapshot(self, snapshot: Dict) -> None:
        """
        Processes the initial snapshot of the order book.

        Parameters
        ----------
        snapshot : Dict
            A dictionary containing the initial state of the asks and bids in the order book.
        """
        self.asks = np.array(snapshot["asks"], dtype=float)
        self.bids = np.array(snapshot["bids"], dtype=float)
        self.sort_book()

    def process(self, recv: Dict) -> None:
        """
        Processes real-time updates to the order book.

        Parameters
        ----------
        recv : Dict
            A dictionary containing the updates to the asks and bids in the order book.
        """
        asks = np.array(recv["data"]["a"], dtype=float)
        bids = np.array(recv["data"]["b"], dtype=float)
        self.asks = self.update_book(self.asks, asks)
        self.bids = self.update_book(self.bids, bids)
        self.sort_book()


class BinanceBBAHandler:
    """
    Handler for processing Best Bid and Ask (BBA) updates from Binance.

    Parameters
    ----------
    ss : SharedState
        An instance of SharedState to store and manage the best bid and ask data.
    """

    def __init__(self, ss) -> None:
        """
        Initializes the BinanceBBAHandler with a reference to a SharedState object.

        Parameters
        ----------
        ss : SharedState
            An instance of SharedState to store and manage the best bid and ask data.
        """
        self.ss = ss

    def process(self, recv: Dict) -> None:
        """
        Processes real-time BBA updates.

        Updates the SharedState with the latest best bid and ask prices along with their quantities.

        Parameters
        ----------
        recv : Dict
            A dictionary containing the latest best bid and ask prices and quantities.
        """
        self.ss.binance_bba[0, 0] = float(recv["data"]["b"])
        self.ss.binance_bba[0, 1] = float(recv["data"]["B"])
        self.ss.binance_bba[1, 0] = float(recv["data"]["a"])
        self.ss.binance_bba[1, 1] = float(recv["data"]["A"])

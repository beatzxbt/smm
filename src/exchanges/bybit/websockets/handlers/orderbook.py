import numpy as np
from typing import Dict, List
from src.exchanges.common.localorderbook import BaseOrderBook

class OrderBookBybit(BaseOrderBook):
    """
    Order book class for Bybit, extending the BaseOrderBook for handling Bybit-specific order book data.

    Methods
    -------
    process_snapshot(asks: List[List[float]], bids: List[List[float]]) -> None:
        Processes the initial snapshot of the order book.
    process(recv: Dict) -> None:
        Processes incoming messages from Bybit to update the order book.
    """

    def process_snapshot(self, asks: List[List[float]], bids: List[List[float]]) -> None:
        """
        Processes and initializes the order book with a snapshot of asks and bids.

        Parameters
        ----------
        asks : List[List[float]]
            A list of ask orders, each represented as [price, quantity].
        bids : List[List[float]]
            A list of bid orders, each represented as [price, quantity].
        """
        self.asks = np.array(asks, dtype=float)
        self.bids = np.array(bids, dtype=float)
        self.sort_book()

    def process(self, recv: Dict) -> None:
        """
        Handles incoming WebSocket messages to update the order book.

        Parameters
        ----------
        recv : Dict
            The incoming message containing either a snapshot or delta update of the order book.
        """
        asks = np.array(recv["data"]["a"], dtype=float)
        bids = np.array(recv["data"]["b"], dtype=float)

        if recv["type"] == "snapshot":
            self.process_snapshot(asks.tolist(), bids.tolist())
        elif recv["type"] == "delta":
            self.asks = self.update_book(self.asks, asks)
            self.bids = self.update_book(self.bids, bids)
            self.sort_book()


class BybitBBAHandler:
    """
    Handler for processing Best Bid and Ask (BBA) updates from Bybit.

    Parameters
    ----------
    ss : SharedState
        An instance of SharedState for managing shared application data.

    Methods
    -------
    process(recv: Dict) -> None:
        Processes real-time BBA updates.
    """

    def __init__(self, ss) -> None:
        """
        Initializes the BybitBBAHandler with a reference to SharedState.

        Parameters
        ----------
        ss : SharedState
            The shared state instance for managing application data.
        """
        self.ss = ss

    def process(self, recv: Dict) -> None:
        """
        Processes real-time updates to the best bid and ask prices and quantities.

        Parameters
        ----------
        recv : Dict
            A dictionary containing the latest BBA prices and quantities.
        """
        best_bid = recv["data"]["b"]
        best_ask = recv["data"]["a"]

        if best_bid:
            price, qty = list(map(float, best_bid[0]))
            if qty > 0:
                self.ss.bybit_bba[0, 0] = price
                self.ss.bybit_bba[0, 1] = qty

        if best_ask:
            price, qty = list(map(float, best_ask[0]))
            if qty > 0:
                self.ss.bybit_bba[1, 0] = price
                self.ss.bybit_bba[1, 1] = qty
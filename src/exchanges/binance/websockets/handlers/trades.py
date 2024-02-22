import numpy as np
from src.sharedstate import SharedState
from typing import Dict, List

class BinanceTradesHandler:
    """
    Handler for processing Binance trade data and updating shared state.

    Parameters
    ----------
    ss : SharedState
        An instance of SharedState to store and manage shared data across different components.

    Attributes
    ----------
    ss : SharedState
        Shared state object where the Binance trades and the last price are stored.
    """

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BinanceTradesHandler with a reference to a SharedState object.

        Parameters
        ----------
        ss : SharedState
            An instance of SharedState to store and manage shared data.
        """
        self.ss = ss

    def initialize(self, data: List[Dict]) -> None:
        """
        Initializes the shared state with historical trade data.

        Parameters
        ----------
        data : List[Dict]
            A list of dictionaries where each dictionary contains information about a single trade.
        """
        for row in data:
            time = float(row["time"])
            price = float(row["price"])
            qty = float(row["qty"])
            side = 1.0 if row["isBuyerMaker"] else 0.0
            new_trade = np.array([[time, side, price, qty]])
            self.ss.binance_trades.append(new_trade)

    def process(self, recv: Dict) -> None:
        """
        Processes a new incoming trade message and updates the shared state accordingly.

        Parameters
        ----------
        recv : Dict
            A dictionary containing information about a single new trade.
        """
        time = float(recv["data"]["T"])
        price = float(recv["data"]["p"])
        qty = float(recv["data"]["q"])
        side = 1.0 if recv["data"]["m"] else 0.0
        new_trade = np.array([[time, side, price, qty]])
        self.ss.binance_trades.append(new_trade)
        self.ss.binance_last_price = float(price)
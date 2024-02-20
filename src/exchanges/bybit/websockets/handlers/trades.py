import numpy as np
from typing import Dict, List
from src.sharedstate import SharedState

class BybitTradesHandler:
    """
    Handler for processing trades data from Bybit and updating the shared state.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState for storing and managing trades data.

    Methods
    -------
    initialize(data: List[Dict]) -> None:
        Initializes the handler with historical trades data.
    process(recv: List[Dict]) -> None:
        Processes real-time trades data received from Bybit.
    """

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BybitTradesHandler with a reference to SharedState.

        Parameters
        ----------
        ss : SharedState
            The shared state instance for managing trades data.
        """
        self.ss = ss

    def initialize(self, data: List[Dict]) -> None:
        """
        Initializes the shared state with historical trades data.

        Parameters
        ----------
        data : List[Dict]
            A list of dictionaries, each representing a trade with time, price, size, and side information.
        """
        for row in data:
            time = float(row["time"])
            price = float(row["price"])
            qty = float(row["size"])
            side = 0.0 if row["side"] == "Buy" else 1.0
            new_trade = np.array([[time, side, price, qty]])
            self.ss.bybit_trades.append(new_trade)

    def process(self, recv: List[Dict]) -> None:
        """
        Processes and updates the shared state with real-time trades data received from Bybit.

        Parameters
        ----------
        recv : List[Dict]
            A list of dictionaries, each representing a trade with time, price, quantity, and side information.
        """
        for trade in recv["data"]:
            time = float(trade["T"])
            price = float(trade["p"])
            qty = float(trade["v"])
            side = 0.0 if trade["S"] == "Buy" else 1.0
            new_trade = np.array([[time, side, price, qty]])
            self.ss.bybit_trades.append(new_trade)
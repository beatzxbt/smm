import numpy as np
from numpy.typing import NDArray
from typing import Dict

class BaseOrderBook:
    """
    A base class for maintaining and updating an order book with ask and bid orders.

    Attributes
    ----------
    asks : NDArray
        A NumPy array to store ask orders. Each order is represented by a [price, quantity] pair.
    bids : NDArray
        A NumPy array to store bid orders. Each order is represented by a [price, quantity] pair.

    Methods
    -------
    sort_book():
        Sorts the ask and bid arrays by price in ascending and descending order, respectively.
    update_book(asks_or_bids: NDArray, data: NDArray) -> NDArray:
        Updates the order book (asks or bids) with new data.
    process(recv):
        Abstract method for processing incoming data. To be implemented by derived classes.
    """

    def __init__(self) -> None:
        """
        Initializes the BaseOrderBook with empty asks and bids arrays.
        """
        self.asks = np.empty((0, 2), dtype=np.float64)
        self.bids = np.empty((0, 2), dtype=np.float64)

    def sort_book(self) -> None:
        """
        Sorts the ask orders in ascending order and bid orders in descending order by price.
        Only keeps the top 500 orders in each.
        """
        self.asks = self.asks[self.asks[:, 0].argsort()][:500]
        self.bids = self.bids[self.bids[:, 0].argsort()[::-1]][:500]

    def update_book(self, asks_or_bids: NDArray, data: NDArray) -> NDArray:
        """
        Updates the specified order book (asks or bids) with new data.

        Parameters
        ----------
        asks_or_bids : NDArray
            The current state of either the asks or bids in the order book.
        data : NDArray
            New data to be integrated into the asks or bids. Each element is a [price, quantity] pair.

        Returns
        -------
        NDArray
            The updated asks or bids array.
        """
        for price, qty in data:
            # Remove orders with the specified price
            asks_or_bids = asks_or_bids[asks_or_bids[:, 0] != price]
            # Add new or updated order if quantity is greater than zero
            if qty > 0:
                asks_or_bids = np.vstack((asks_or_bids, np.array([price, qty])))

        return asks_or_bids

    def process(self, recv: Dict) -> Exception:
        """
        Abstract method for processing incoming data. To be implemented by derived classes.

        Parameters
        ----------
        recv : Any
            The incoming data to process.

        Raises
        ------
        NotImplementedError
            If the method is not overridden in a derived class.
        """
        raise NotImplementedError("Derived classes should implement this method")

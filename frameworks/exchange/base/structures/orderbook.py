import numpy as np
from typing import Union
from numpy.typing import NDArray


class Orderbook:
    """
    An orderbook class, maintaining separate arrays for bid and 
    ask orders with functionality to initialize, update, and sort 
    the orders.

    Attributes
    ----------
    size : int
        The maximum number of bid/ask pairs the order book will hold.

    asks : NDArray
        Array to store ask orders, each with price and quantity.

    bids : NDArray
        Array to store bid orders, each with price and quantity.

    bba : NDArray
        Array to store best bid and ask, each with price and quantity.
    """
    def __init__(self, size: int):
        self.size = size
        self.asks = np.empty(shape=(self.size, 2), dtype=np.float64)
        self.bids = np.empty_like(self.asks)
        self.bba = np.empty((2, 2), dtype=np.float64)

    def _sort_book_(self) -> NDArray:
        """
        Constructs all the necessary attributes for the orderbook object.

        Parameters
        ----------
        size : int
            Size of the order book (number of orders to store).
        """
        self.asks = self.asks[self.asks[:, 0].argsort()][:self.size]
        self.bids = self.bids[self.bids[:, 0].argsort()][::-1][:self.size]
        self.bba[0, :] = self.bids[0]
        self.bba[1, :] = self.asks[0]

    def _process_book_(book: NDArray, new_data: NDArray) -> NDArray:
        """
        Updates the given book with new data. Removes entries with matching 
        prices in new_data and adds non-zero quantity data from new_data to the book.

        Parameters
        ----------
        book : NDArray
            The existing orderbook data (either bids or asks).

        new_data : NDArray
            New order data to be processed into the book.

        Returns
        -------
        NDArray
            The updated order book data.
        """
        book = book[~np.isin(
            book[:, 0],
            np.concatenate([
                new_data[new_data[:, 1] == 0, 0],
                new_data[:, 0]
            ])
        )]
        non_zero_qty_new_data = new_data[new_data[:, 1] != 0]
        return np.vstack((book, non_zero_qty_new_data))

    def initialize(self, asks: NDArray, bids: NDArray) -> NDArray:
        """
        Initializes the order book with given ask and bid data and sorts the book.

        Parameters
        ----------
        asks : NDArray
            Initial ask orders data, formatted as [[price, quantity], ...].

        bids : NDArray
            Initial bid orders data, formatted as [[price, quantity], ...].
        """
        self.asks = np.array(asks, dtype=np.float64)
        self.bids = np.array(bids, np.float64)
        self._sort_book_()

    def update_book(self, asks: NDArray, bids: NDArray) -> NDArray:
        """
        Updates the order book with new ask and bid data.

        Parameters
        ----------
        asks : NDArray
            Initial ask orders data, formatted as [[price, quantity], ...].

        bids : NDArray
            Initial bid orders data, formatted as [[price, quantity], ...].
            
        timestamp : Union[int, float]
            Timestamp of the update.
        """
        self.asks = self._process_book_(self.asks, asks)
        self.bids = self._process_book_(self.bids, bids)
        self._sort_book_()
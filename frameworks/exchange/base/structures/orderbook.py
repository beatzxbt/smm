import numpy as np
from numba.types import int64, float64, Array
from numba.experimental import jitclass

from frameworks.tools.numba import nbisin

spec = [
    ("size", int64),
    ("asks", float64[:, :]),
    ("bids", float64[:, :]),
    ("bba", float64[:, :])
]

@jitclass(spec)
class Orderbook:
    """
    An orderbook class, maintaining separate arrays for bid and 
    ask orders with functionality to initialize, update, and sort 
    the orders.

    Attributes
    ----------
    size : int
        The maximum number of bid/ask pairs the order book will hold.

    asks : Array
        Array to store ask orders, each with price and quantity.

    bids : Array
        Array to store bid orders, each with price and quantity.

    bba : Array
        Array to store best bid and ask, each with price and quantity.
    """
    def __init__(self, size: int) -> None:
        """
        Constructs all the necessary attributes for the orderbook object.

        Parameters
        ----------
        size : int
            Size of the order book (number of orders to store).
        """
        self.size = size
        self.asks = np.zeros((self.size, 2), dtype=float64)
        self.bids = np.zeros((self.size, 2), dtype=float64)
        self.bba = np.zeros((2, 2), dtype=float64)

    def sort_bids(self) -> None:
        """
        Sorts the bid orders in descending order of price and updates the best bid.
        """
        self.bids = self.bids[self.bids[:, 0].argsort()][::-1][:self.size]
        self.bba[0, :] = self.bids[0]

    def sort_asks(self) -> None:
        """
        Sorts the ask orders in ascending order of price and updates the best ask.
        """
        self.asks = self.asks[self.asks[:, 0].argsort()][:self.size]
        self.bba[1, :] = self.asks[0]        
    
    def refresh(self, asks: Array, bids: Array) -> None:
        """
        Refreshes the order book with given *complete* ask and bid data and sorts the book.

        Parameters
        ----------
        asks : Array
            Initial ask orders data, formatted as [[price, size], ...].

        bids : Array
            Initial bid orders data, formatted as [[price, size], ...].
        """
        # Completely reset all arrays
        self.asks = np.zeros_like(self.asks)
        self.bids = np.zeros_like(self.bids)
        self.bba = np.zeros_like(self.bba)

        self.asks[:, :] = asks[:min(asks.shape[0], self.size), :]
        self.bids[:, :] = bids[:min(bids.shape[0], self.size), :]
        self.sort_bids()
        self.sort_asks()

    def update_bids(self, bids: Array) -> None:
        """
        Updates the current bids with new data. Removes entries with matching 
        prices in update, regardless of size, and then adds non-zero quantity 
        data from update to the book.

        Parameters
        ----------
        bids : Array
            New bid orders data, formatted as [[price, size], ...].
        """
        if bids.size == 0:
            return None
        
        self.bids = self.bids[~nbisin(self.bids[:, 0], bids[:, 0])]
        self.bids = np.vstack((self.bids, bids[bids[:, 1] != 0]))
        self.sort_bids()

    def update_asks(self, asks: Array) -> None:
        """
        Updates the current asks with new data. Removes entries with matching 
        prices in update, regardless of size, and then adds non-zero quantity 
        data from update to the book.

        Parameters
        ----------
        asks : Array
            New ask orders data, formatted as [[price, size], ...].
        """
        if asks.size == 0:
            return None
        
        self.asks = self.asks[~nbisin(self.asks[:, 0], asks[:, 0])]
        self.asks = np.vstack((self.asks, asks[asks[:, 1] != 0]))
        self.sort_asks()

    def update_full(self, asks: Array, bids: Array) -> None:
        """
        Updates the order book with new ask and bid data.

        Parameters
        ----------
        asks : Array
            New ask orders data, formatted as [[price, size], ...].

        bids : Array
            New bid orders data, formatted as [[price, size], ...].
        """
        self.update_asks(asks)
        self.update_bids(bids)

    def get_mid(self) -> float:
        """
        Calculates the mid price of the order book based on the best bid and ask prices.

        Returns
        -------
        float
            The mid price, which is the average of the best bid and best ask prices.
        """
        return (self.bba[0, 0] + self.bba[1, 0])/2

    def get_wmid(self) -> float:
        """
        Calculates the weighted mid price of the order book, considering the volume imbalance 
        between the best bid and best ask.

        Returns
        -------
        float
            The weighted mid price, which accounts for the volume imbalance at the top of the book.
        """
        imb = self.bba[0, 1] / (self.bba[0, 1] + self.bba[1, 1])
        return self.bba[0, 0] * imb + self.bba[1, 0] * (1 - imb)
    
    def get_vamp(self, depth: float) -> float:
        """
        Calculates the volume-weighted average market price (VAMP) up to a specified depth for both bids and asks.

        Parameters
        ----------
        depth : float
            The depth (in terms of volume) up to which the VAMP is calculated.

        Returns
        -------
        float
            The VAMP, representing an average price weighted by order sizes up to the specified depth.
        """
        bid_size_weighted_sum = 0.0
        ask_size_weighted_sum = 0.0
        bid_cum_size = 0.0
        ask_cum_size = 0.0
        
        # Calculate size-weighted sum for bids
        for price, size in self.bids:
            if bid_cum_size + size > depth:
                remaining_size = depth - bid_cum_size
                bid_size_weighted_sum += price * remaining_size
                bid_cum_size += remaining_size
                break

            bid_size_weighted_sum += price * size
            bid_cum_size += size
            
            if bid_cum_size >= depth:
                break
        
        # Calculate size-weighted sum for asks
        for price, size in self.asks:
            if ask_cum_size + size > depth:
                remaining_size = depth - ask_cum_size
                ask_size_weighted_sum += price * remaining_size
                ask_cum_size += remaining_size
                break

            ask_size_weighted_sum += price * size
            ask_cum_size += size

            if ask_cum_size >= depth:
                break

        total_size = bid_cum_size + ask_cum_size

        if total_size == 0:
            return 0.0
        
        return (bid_size_weighted_sum + ask_size_weighted_sum) / total_size
    
    def get_spread(self) -> float:
        """
        Calculates the current spread of the order book.

        Returns
        -------
        float
            The spread, defined as the difference between the best ask and the best bid prices.
        """
        return self.bba[1, 0] - self.bba[0, 0]
    
    def get_slippage(self, book: Array, size: float) -> float:
        """
        Calculates the slippage cost for a hypothetical order of a given size, based on either the bid or ask side of the book.

        Parameters
        ----------
        book : Array
            The order book data for the side (bids or asks) being considered.

        size : float
            The size of the hypothetical order for which slippage is being calculated.

        Returns
        -------
        float
            The slippage cost, defined as the volume-weighted average deviation from the mid price for the given order size.
        """
        mid = self.get_mid()
        cum_size = 0.0
        slippage = 0.0

        for level in range(book.shape[0]):
            cum_size += book[level, 1]
            slippage += np.abs(mid - book[level, 0]) * book[level, 1]

            if cum_size >= size:
                slippage /= cum_size
                break
        
        return slippage if slippage <= mid else mid
import numpy as np
from numba.experimental import jitclass
from numba.types import uint32, int32, float64
from numba.experimental import jitclass


@jitclass
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

    size: uint32
    asks: float64[:, :]
    bids: float64[:, :]
    bba: float64[:, :]
    seq_id: int32

    def __init__(self, size: int) -> None:
        """
        Constructs all the necessary attributes for the orderbook object.

        Parameters
        ----------
        size : int
            Size of the order book (number of orders to store).
        """
        self.size: int = size
        self.asks: np.ndarray = np.zeros((self.size, 2), dtype=float64)
        self.bids: np.ndarray = np.zeros((self.size, 2), dtype=float64)
        self.bba: np.ndarray = np.zeros((2, 2), dtype=float64)
        self.seq_id: int = 0
    
    def reset(self) -> None:
        """
        Sets all attribute values back to 0 
        """
        self.asks.fill(0)
        self.bids.fill(0)
        self.bba.fill(0)
        self.seq_id = 0
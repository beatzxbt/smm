from abc import ABC, abstractmethod
from typing import Dict, List, Union

from frameworks.tools.logging import time_ms
from frameworks.exchange.base.structures.orderbook import Orderbook


class OrderbookHandler(ABC):
    """
    A base class for handling order book data.

    This class provides methods for managing order book data,
    including abstract methods for refreshing and processing
    order book data, which should be implemented by subclasses.
    """

    def __init__(self, orderbook: Orderbook) -> None:
        """
        Initializes the OrderbookHandler class with an Orderbook instance.

        Parameters
        ----------
        orderbook : Orderbook
            An Orderbook instance to manage order book data.
        """
        self.orderbook = orderbook
        self.timestamp = time_ms()

    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the order book data with new data.

        This method should be implemented by subclasses to process
        new order book data and update the order book.

        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the order book data.

        Steps
        -----
        1. Separate the recv payload into bids and asks.
           -> They should be in the format [Price, Size] per level.
        2. Wrap the lists into numpy arrays (dtype must be np.float64).
        3. Call self.orderbook.refresh(asks, bids).
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming order book data to update the Orderbook.

        This method should be implemented by subclasses to process
        incoming order book data and update the Orderbook.

        Parameters
        ----------
        recv : Dict
            The received payload containing the order book data.

        Steps
        -----
        1. Separate the recv payload into bids and asks.
           -> They should be in the format [Price, Size] per level.
        2. Wrap the lists into numpy arrays (dtype must be np.float64).
        3. Call self.orderbook.update_full(asks, bids) if timestamp > self.timestamp.
        4. Update self.timestamp with the new timestamp.
        """
        pass

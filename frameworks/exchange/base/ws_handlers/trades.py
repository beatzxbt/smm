from abc import ABC, abstractmethod
from typing import Dict, List, Union

from frameworks.exchange.base.structures.trades import Trade, Trades


class TradesHandler(ABC):
    """
    A base class for handling trades data.

    This class provides methods for managing trades data,
    including abstract methods for refreshing and processing
    trades data, which should be implemented by subclasses.
    """

    def __init__(self, trades: Trades) -> None:
        """
        Initializes the TradesHandler class with a Trades instance.

        Parameters
        ----------
        trades : Trades
            A Trades instance to store trades data.
        """
        self.trades = trades

    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the trades data with new data.

        This method should be implemented by subclasses to process
        new trades data and update the trades RingBuffer.

        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the trades data.

        Steps
        -----
        1. Extract the list of trades from the recv payload.
           -> Ensure the following data points are present:
                - Timestamp
                - Side
                - Price
                - Size
        2. Create Trade instances with the respective values.
        3. Call 'self.trades.add_many(trades)' to add the trades to the RingBuffer.
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming trades data to update the RingBuffer.

        This method should be implemented by subclasses to process
        incoming trades data and update the trades RingBuffer.

        Parameters
        ----------
        recv : Dict
            The received payload containing the trades data.

        Steps
        -----
        1. Extract the trades data from the recv payload.
           -> Ensure the following data points are present:
                - Timestamp
                - Side
                - Price
                - Size
        2. Create a Trade instance with the respective values.
        3. Call 'self.trades.add_single(trade)' to add the trade to the RingBuffer.
        """
        pass

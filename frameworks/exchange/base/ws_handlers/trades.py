import numpy as np
from numpy_ringbuffer import RingBuffer
from abc import ABC, abstractmethod
from typing import Dict, List, Union


class TradesHandler(ABC):
    """
    A base class for handling trades data.

    This class provides methods for managing trades data,
    including abstract methods for refreshing and processing
    trades data, which should be implemented by subclasses.
    """

    def __init__(self, trades: RingBuffer) -> None:
        """
        Initializes the TradesHandler class with a RingBuffer for trades.

        Parameters
        ----------
        trades : RingBuffer
            A RingBuffer instance to store trades data.
        """
        self.trades = trades
        self.format = np.array([0.0, 0.0, 0.0, 0.0])  # [Time, Side, Price, Size]

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
        2. Overwrite the self.format array with the correct values and call 'self.trades.append(self.format.copy())'.
           -> Remember to call this for each trade in your list.
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
        2. Overwrite the self.format array with the correct values.
        3. Call 'self.trades.append(self.format.copy())'.
        """
        pass

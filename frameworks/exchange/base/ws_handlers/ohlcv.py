import numpy as np
from numpy_ringbuffer import RingBuffer
from abc import ABC, abstractmethod
from typing import Dict, List, Union


class OhlcvHandler(ABC):
    """
    A base class for handling OHLCV (Open, High, Low, Close, Volume) data.

    This class provides methods for clearing the OHLCV RingBuffer and
    abstract methods for refreshing and processing OHLCV data, which
    should be implemented by subclasses.
    """

    def __init__(self, ohlcv: RingBuffer) -> None:
        """
        Initializes the OhlcvHandler class with an OHLCV RingBuffer.

        Parameters
        ----------
        ohlcv : RingBuffer
            A RingBuffer instance to store OHLCV data.
        """
        self.ohlcv = ohlcv
        self.format = np.array(
            [
                0.0,  # Open Timestamp
                0.0,  # Open
                0.0,  # High
                0.0,  # Low
                0.0,  # Close
                0.0,  # Volume
            ]
        )

    def clear_ohlcv_ringbuffer(self) -> None:
        """
        Clears the OHLCV RingBuffer.

        This method removes all elements from the OHLCV RingBuffer.
        """
        for _ in range(self.ohlcv.shape[0]):
            self.ohlcv.pop()

    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the OHLCV data with new data.

        This method should be implemented by subclasses to process
        new OHLCV data and update the OHLCV RingBuffer.

        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the OHLCV data.

        Steps
        -----
        1. Extract the OHLCV list from the recv payload.
           -> Ensure the following data points are present:
                - Timestamp
                - Open
                - High
                - Low
                - Close
                - Volume
        2. Overwrite the self.format array with the correct values
           and call 'self.ohlcv.append(self.format.copy())'.
           -> Remember to call this for each candle in the OHLCV list.
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming OHLCV data to update the RingBuffer.

        This method should be implemented by subclasses to process
        incoming OHLCV data and update the OHLCV RingBuffer.

        Parameters
        ----------
        recv : Dict
            The received payload containing the OHLCV data.

        Steps
        -----
        1. Extract the OHLCV list from the recv payload.
           -> Ensure the following data points are present:
                - Timestamp
                - Open
                - High
                - Low
                - Close
                - Volume
        2. Overwrite the self.format array with the correct values.
        3. If the candle is new (not an update), call 'self.ohlcv.append(self.format.copy())'.
           -> Remember to check that the candle is not new before appending!
        """
        pass

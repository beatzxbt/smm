from abc import ABC, abstractmethod
from typing import Dict, List, Union

from frameworks.exchange.base.structures.ohlcv import OHLCV, Candles


class OhlcvHandler(ABC):
    """
    A base class for handling OHLCV (Open, High, Low, Close, Volume) data.

    This class provides methods for clearing the OHLCV RingBuffer and
    abstract methods for refreshing and processing OHLCV data, which
    should be implemented by subclasses.
    """

    def __init__(self, ohlcv: Candles) -> None:
        """
        Initializes the OhlcvHandler class with an OHLCV Candles instance.

        Parameters
        ----------
        ohlcv : Candles
            A Candles instance to store OHLCV data.
        """
        self.ohlcv: Candles = ohlcv

    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the Candles structure with new data.

        This method should be implemented by subclasses to process
        new OHLCV data and update the Candles instance.

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
        2. Create OHLCV objects for each candle in the list.
        3. Add each OHLCV object to the self.ohlcv using either add_single/add_many methods.
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming OHLCV data to update the Candles instance.

        This method should be implemented by subclasses to process
        incoming OHLCV data and update the Candles instance.

        Parameters
        ----------
        recv : Dict
            The received payload containing the OHLCV data.

        Steps
        -----
        1. Extract the OHLCV data from the recv payload.
           -> Ensure the following data points are present:
                - Timestamp
                - Open
                - High
                - Low
                - Close
                - Volume
        2. Create an OHLCV object with the extracted data.
        3. Add the OHLCV object to the self.ohlcv using the add_single method.
        """
        pass

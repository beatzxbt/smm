from abc import ABC, abstractmethod
from typing import Dict


class TickerHandler(ABC):
    """
    A base class for handling ticker data.

    This class provides methods for managing ticker data,
    including abstract methods for refreshing and processing
    ticker data, which should be implemented by subclasses.
    """

    def __init__(self, ticker: Dict) -> None:
        """
        Initializes the TickerHandler class with a ticker dictionary.

        Parameters
        ----------
        ticker : dict
            A dictionary to store ticker data.
        """
        self.ticker = ticker
        self.format = {
            "markPrice": 0.0,
            "indexPrice": 0.0,
            "fundingTime": 0.0,
            "fundingRate": 0.0,
        }

    @abstractmethod
    def refresh(self, recv: Dict) -> None:
        """
        Refreshes the ticker data with new data.

        This method should be implemented by subclasses to process
        new ticker data and update the ticker dictionary.

        Parameters
        ----------
        recv : Dict
            The received payload containing the ticker data.
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming ticker data to update the ticker dictionary.

        This method should be implemented by subclasses to process
        incoming ticker data and update the ticker dictionary.

        Parameters
        ----------
        recv : Dict
            The received payload containing the ticker data.

        Steps
        -----
        1. Extract the ticker data from the recv payload.
           -> Ensure the following data points are present:
                - Mark price
                - Index price (if not available, use mark/oracle price)
                - Next funding timestamp
                - Funding rate
        2. Overwrite the self.format dict with the respective values.
        3. Call self.ticker.update(self.format).
        """
        pass

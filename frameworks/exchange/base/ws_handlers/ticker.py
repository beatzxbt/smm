from abc import ABC, abstractmethod
from typing import Dict, List, Union

from frameworks.exchange.base.structures.ticker import Ticker


class TickerHandler(ABC):
    """
    A base class for handling ticker data.

    This class provides methods for managing ticker data,
    including abstract methods for refreshing and processing
    ticker data, which should be implemented by subclasses.
    """

    def __init__(self, ticker: Ticker) -> None:
        """
        Initializes the TickerHandler class with a Ticker instance.

        Parameters
        ----------
        ticker : Ticker
            An instance to store ticker data.
        """
        self.ticker = ticker

    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the ticker data with new data.

        This method should be implemented by subclasses to process
        new ticker data and update the ticker instance.

        Parameters
        ----------
        recv : Dict
            The received payload containing the ticker data.

        Steps
        -----
        1. Extract the ticker data from the recv payload. Ensure *at least* the following data points are present:
            - Next funding timestamp
            - Funding rate
            - Mark price
            - Index price (if not available, use mark/oracle price)

        2. Update the relevant self.ticker attributes using self.ticker.update()
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming ticker data to update the ticker instance.

        This method should be implemented by subclasses to process
        incoming ticker data and update the ticker instance.

        Parameters
        ----------
        recv : Dict
            The received payload containing the ticker data.

        Steps
        -----
        1. Extract the ticker data from the recv payload.
        2. Update the relevant self.position attributes using self.position.update()
        """
        pass

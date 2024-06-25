from abc import ABC, abstractmethod
from typing import Dict, List, Union


class PositionHandler(ABC):
    """
    A base class for handling position data.

    This class provides methods for managing position data,
    including abstract methods for refreshing and processing
    position data, which should be implemented by subclasses.
    """

    def __init__(self, position: Dict) -> None:
        """
        Initializes the PositionHandler class with a position dictionary.

        Parameters
        ----------
        position : dict
            A dictionary to store position data.
        """
        self.position = position
        self.format = {
            "createTime": 0.0,
            "price": 0.0, 
            "size": 0.0, 
            "uPnl": 0.0
        }

    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the position data with new data.

        This method should be implemented by subclasses to process
        new position data and update the position dictionary.

        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the position data.

        Steps
        -----
        1. Extract the position from the recv payload.
           -> Ensure the following data points are present:
                - Price
                - Size
                - Unrealized PnL
        2. Overwrite self.format with the respective values.
        3. Call self.position.update(self.format).
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming position data to update the position dictionary.

        This method should be implemented by subclasses to process
        incoming position data and update the position dictionary.

        Parameters
        ----------
        recv : Dict
            The received payload containing the position data.

        Steps
        -----
        1. Extract the position from the recv payload.
           -> Ensure the following data points are present:
                - Price
                - Size
                - Unrealized PnL
        2. Overwrite self.format with the respective values.
        3. Call self.position.update(self.format).
        """
        pass

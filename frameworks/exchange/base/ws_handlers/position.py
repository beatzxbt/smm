from abc import ABC, abstractmethod
from typing import Dict, List, Union

from frameworks.exchange.base.structures.position import Position


class PositionHandler(ABC):
    """
    A base class for handling position data.

    This class provides methods for managing position data,
    including abstract methods for refreshing and processing
    position data, which should be implemented by subclasses.
    """

    def __init__(self, position: Position) -> None:
        """
        Initializes the PositionHandler class with a position data structure.

        Parameters
        ----------
        position : Position
            A structure to store position data.
        """
        self.position = position

    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the position data with new data.

        This method should be implemented by subclasses to process
        new position data and update the position instance.

        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the position data.

        Steps
        -----
        1. Extract the position from the recv payload. Ensure *at least* the following data points are present:
            - Side
            - Price
            - Size
            - uPnl

        2. Create a Position instance with the respective values.
        3. Reassign self.position to the new Position() instance.
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming position data to update the position instance.

        This method should be implemented by subclasses to process
        incoming position data and update the position instance.

        Parameters
        ----------
        recv : Dict
            The received payload containing the position data.

        Steps
        -----
        1. Extract the position from the recv payload. Ensure *at least* the following data points are present:
            - Side
            - Price
            - Size
            - uPnl

        2. Update the relevant self.position attributes using self.position.update()
        """
        pass

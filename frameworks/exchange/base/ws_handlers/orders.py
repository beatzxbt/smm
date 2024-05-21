from abc import ABC, abstractmethod
from typing import Dict, List, Union

class OrdersHandler(ABC):
    """
    A base class for handling orders data.

    This class provides methods for managing orders data,
    including abstract methods for refreshing and processing 
    orders data, which should be implemented by subclasses.
    """
    def __init__(self, orders: Dict) -> None:
        """
        Initializes the OrdersHandler class with an orders dictionary.

        Parameters
        ----------
        orders : dict
            A dictionary to store orders data.
        """
        self.orders = orders
        self.format = {
            "createTime": 0.0,
            "side": 0.0,
            "price": 0.0,
            "size": 0.0
        }
    
    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the orders data with new data.

        This method should be implemented by subclasses to process
        new orders data and update the orders dictionary.

        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the orders data.

        Steps
        -----
        1. Extract the orders list from the recv payload.
           -> Ensure the following data points are present:
                - OrderId
                - Create Time
                - Side
                - Price
                - Size
        2. For each order in the list:
           -> Overwrite self.format with the respective values.
           -> self.orders[OrderId] = self.format.copy().
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming orders data to update the orders dictionary.

        This method should be implemented by subclasses to process
        incoming orders data and update the orders dictionary.

        Parameters
        ----------
        recv : Dict
            The received payload containing the orders data.

        Steps
        -----
        1. Extract the orders list from the recv payload.
           -> Ensure the following data points are present:
                - OrderId
                - Create Time
                - Side
                - Price
                - Size
        2. For each order in the payload:
           -> Overwrite self.format with the respective values.
           -> self.orders[OrderId] = self.format.copy().
        3. If any orders need to be deleted:
           -> del self.orders[OrderId].
        """
        pass

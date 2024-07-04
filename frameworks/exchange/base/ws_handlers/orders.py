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
        1. Extract the orders from the recv payload. Ensure *at least* the following data points are present:
            - orderId or clientOrderId
            - side
            - price
            - size

        2. For each order:
           - Create an Order() instance with the respective values.
           - self.orders[orderId or clientOrderId] = Order()
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
        1. Extract the orders from the recv payload. Ensure *at least* the following data points are present:
            - orderId or clientOrderId
            - side
            - price
            - size

        2. For each order:
           a. Create an Order() instance with the respective values.
           b. self.orders[orderId or clientOrderId] = Order()

        3. If any orders need to be deleted:
           a. del self.orders[orderId or clientOrderId].
        """
        pass

from abc import ABC, abstractmethod
from typing import Dict, List, Union

from frameworks.exchange.base.structures.order import Order, Orders


class OrdersHandler(ABC):
    """
    A base class for handling private order data.

    This class provides methods for managing orders data,
    including abstract methods for refreshing and processing
    orders data, which should be implemented by subclasses.
    """

    def __init__(self, orders: Orders) -> None:
        """
        Initializes the OrdersHandler class with an Orders instance.

        Parameters
        ----------
        orders : Orders
            An Orders instance to store orders data.
        """
        self.orders = orders

    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the orders data with new data.

        This method should be implemented by subclasses to process
        new orders data and update the Orders instance.

        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the orders data.

        Steps
        -----
        1. Extract the orders from the recv payload. Ensure *at least* the following data points are present:
            - orderId/clientOrderId
            - side
            - price
            - size

        2. For each order:
           - Create an Order instance with the respective values.
           - Add the Order to the Orders instance using add_single/add_many methods.
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming orders data to update the Orders instance.

        This method should be implemented by subclasses to process
        incoming orders data and update the Orders instance.

        Parameters
        ----------
        recv : Dict
            The received payload containing the orders data.

        Steps
        -----
        1. Extract the orders from the recv payload. Ensure *at least* the following data points are present:
            - orderId/clientOrderId
            - side
            - price
            - size

        2. For each order:
           a. Create an Order instance with the respective values.
           b. Add the Order to the Orders instance using add_single/add_many methods.

        3. If any orders need to be deleted:
           a. Use del self.orders[orderId/clientOrderId] to delete the order.
        """
        pass

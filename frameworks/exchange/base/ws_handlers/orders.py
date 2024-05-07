from abc import ABC, abstractmethod
from typing import Dict, List, Union

class OrdersHandler(ABC):
    def __init__(self, current_orders: Dict) -> None:
        self.current_orders = current_orders
        self.single_order = {
            "createTime": 0,
            "side": "",
            "price": 0.0,
            "size": 0.0
        }
    
    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        1. Extract the orders list your recv payload
            -> Make sure you have the following data points:
                - OrderId
                - Create Time
                - Side
                - Price
                - Size

        2. For each order in the list:
            -> Overwrite self.single_order with the respective values
            -> self.current_orders[OrderId] = self.single_order.copy()
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        1. Extract the orders from your recv payload:
            -> Make sure you have the following data points:
                - OrderId
                - Create Time
                - Side
                - Price
                - Size

        2. For each order in your payload:
            -> Overwrite self.single_order with the respective values
            -> self.current_orders[OrderId] = self.single_order.copy()

        3. If any orders need to be deleted:
            -> del self.orders[OrderId]
        """
        pass

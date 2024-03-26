from abc import ABC, abstractmethod
from typing import Dict, List, Union

class PositionHandler(ABC):
    def __init__(self, current_position: Dict) -> None:
        self.current_position = current_position
        self.position = {
            "price": 0,
            "size": 0,
            "uPnL": 0
        }
    
    @abstractmethod
    def sync(self, recv: Union[Dict, List]) -> None:
        """
        1. Extract the position from your recv payload
            -> Make sure you have the following data points:
                - Price
                - Size
                - Unrealized PnL

        2. Overwrite self.position with it's respective values
        3. Call self.current_position.update(self.position)
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        1. Extract the position from your recv payload
            -> Make sure you have the following data points:
                - Price
                - Size
                - Unrealized PnL

        2. Overwrite self.position with it's respective values
        3. Call self.current_position.update(self.position)
        """
        pass
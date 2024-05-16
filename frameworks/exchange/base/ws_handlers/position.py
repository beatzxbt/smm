from abc import ABC, abstractmethod
from typing import Dict, List, Union

class PositionHandler(ABC):
    def __init__(self, position: Dict) -> None:
        self.position = position
        self.format = {
            "price": 0.0,
            "size": 0.0,
            "uPnL": 0.0
        }
    
    @abstractmethod
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        1. Extract the position from your recv payload
            -> Make sure you have the following data points:
                - Price
                - Size
                - Unrealized PnL

        2. Overwrite self.format with it's respective values
        3. Call self.position.update(self.format)
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

        2. Overwrite self.format with it's respective values
        3. Call self.position.update(self.format)
        """
        pass
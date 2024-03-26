import numpy as np
from numpy_ringbuffer import RingBuffer
from abc import ABC, abstractmethod
from typing import Dict, List, Union

class TradesHandler(ABC):
    def __init__(self, trades: RingBuffer) -> None:
        self.trades = trades
        self.format = np.array([
            0., # Time
            0., # Side 
            0., # Price     
            0.  # Size 
        ])
    
    @abstractmethod
    def initialize(self, recv: Union[Dict, List]) -> None:
        """
        1. Extract the list of trades from your recv payload.
            -> Make sure you have the following data points:
                - Timestamp
                - Side
                - Price
                - Size
        2. Overwrite the self.format array in the correct form and call 'self.trades.append(self.format.copy())':
            -> Remember to call this for each trade in your list
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        1. Extract the trades data your recv payload
            -> Make sure you have the following data points:
                - Timestamp
                - Side
                - Price
                - Size

        2. Overwrite the self.format array in the correct format.
        3. Call self.trades.append(self.format.copy())
        """
        pass
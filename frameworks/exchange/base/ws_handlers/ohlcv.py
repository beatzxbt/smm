import numpy as np
from numpy_ringbuffer import RingBuffer
from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional

class OhlcvHandler(ABC):
    def __init__(self, ohlcv: RingBuffer) -> None:
        self.ohlcv = ohlcv
        self.format = np.array([
            0.0, # Open Timestamp
            0.0, # Open     
            0.0, # High 
            0.0, # Low 
            0.0, # Close 
            0.0, # Volume
        ])
    
    @abstractmethod
    def initialize(self, recv: Union[Dict, List]) -> None:
        """
        1. Extract the ohlcv list your recv payload
            -> Make sure you have the following data points:
                - Timestamp
                - Open
                - High
                - Low
                - Close
                - Volume 
        2. Overwrite the self.format array in the correct form and call 'self.ohlcv.append(self.format.copy())':
            -> Remember to call this for each candle in your ohlcv list
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        1. Extract the ohlcv list your recv payload
            -> Make sure you have the following data points:
                - Timestamp
                - Open
                - High
                - Low
                - Close
                - Volume 

        2. Overwrite the self.format array in the correct format
        2. If your candle is new (not an update), call self.ohlcv.append(self.format.copy()):
            -> Remember to check that the candle is not new!
        """
        pass
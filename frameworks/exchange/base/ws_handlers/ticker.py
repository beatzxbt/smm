import numpy as np
from numpy_ringbuffer import RingBuffer
from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional

class TickerHandler(ABC):
    def __init__(self, ticker: Dict) -> None:
        self.ticker = ticker
        self.format = {
            "markPrice": 0.0,
            "indexPrice": 0.0,
            "fundingTime": 0.0,
            "fundingRate": 0.0
        }

    @abstractmethod
    def refresh(self, recv: Dict) -> None:
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        1. Extract the ticker data from your recv payload
            -> Make sure you have the following data points:
                - Mark price
                - Index price (if you dont have this, just use mark/oracle price)
                - Next funding timestamp
                - Funding rate

        2. Overwrite the self.format dict with its respective values
        3. Call self.ticker.update(self.format)
        """
        pass
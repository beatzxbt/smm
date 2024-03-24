import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Union
from frameworks.tools.logging import time_ms
from frameworks.exchange.base.structures.orderbook import Orderbook

class OrderbookHandler(ABC):
    def __init__(self, orderbook: Orderbook) -> None:
        self.orderbook = orderbook
        self.timestamp = time_ms()
        self.bids = np.array([[0., 0.]], dtype=np.float64)
        self.asks = np.array([[0., 0.]], dtype=np.float64)
    
    @abstractmethod
    def initialize(self, recv: Union[Dict, List]) -> None:
        """
        1. Seperate your recv payload into bids and asks
            -> They should be in the format [Price, Size] per level
        2. Wrap the lists into numpy arrays (overwrite self.bids & self.asks)
        3. Call self.orderbook.initialize(self.asks, self.bids)
        """
        pass

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        1. Seperate your recv payload into bids and asks
            -> They should be in the format [Price, Size] per level
        2. Wrap the lists into numpy arrays (overwrite self.bids & self.asks)
        3. Get the timestamp of the update and update self.timestamp
        4. Call self.orderbook.update(self.asks, self.bids, timestamp)
        """
        pass
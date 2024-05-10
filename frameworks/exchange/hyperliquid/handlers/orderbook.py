import numpy as np
from typing import List, Dict, Union

from frameworks.sharedstate import SharedState
from frameworks.exchange.base.ws_handlers.orderbook import OrderbookHandler


class HyperliquidOrderbookHandler(OrderbookHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.orderbook)
        self.update_time = 0
    
    def full_orderbook_update(self, recv: Dict) -> None:
        self.bids = np.array(recv["levels"][0], dtype=np.float64)[:, 0:2]
        self.asks = np.array(recv["levels"][1], dtype=np.float64)[:, 0:2]

    def refresh(self, recv: Dict) -> None:
        self.update_time = int(recv["time"])
        self.full_orderbook_update(recv)
        self.orderbook.initialize(self.asks, self.bids)

    def process(self, recv: Dict) -> None:
        new_update_time = int(recv["time"])
        
        if new_update_time > self.update_time:
            self.update_time = new_update_time
            self.full_orderbook_update(recv)
            self.orderbook.update_book(self.asks, self.bids)
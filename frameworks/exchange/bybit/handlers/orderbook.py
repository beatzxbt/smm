import numpy as np
from typing import List, Dict, Union
from frameworks.exchange.base.ws_handlers.orderbook import OrderbookHandler
from frameworks.sharedstate import SharedState

class BybitOrderbookHandler(OrderbookHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.orderbook)
        self.update_id = 0
    
    def bba_update(self, recv: Dict) -> None:
        """Unused for now"""
        self.orderbook.bba[0, :] = tuple(map(float, recv["a"]))
        self.orderbook.bba[1, :] = tuple(map(float, recv["b"]))

    def full_orderbook_update(self, recv: Dict) -> None:
        self.bids = np.array(recv["a"], dtype=np.float64)
        self.asks = np.array(recv["b"], dtype=np.float64)

    def initialize(self, recv: Dict) -> None:
        self.update_id = int(recv["seq"])
        self.full_orderbook_update(recv)
        self.orderbook.initialize(self.asks, self.bids)

    def process(self, recv: Dict) -> None:
        new_update_id = int(recv["seq"])

        if new_update_id == 1:
            self.update_id = new_update_id
            self.full_orderbook_update(recv["data"])
            self.orderbook.initialize(self.asks, self.bids)
        
        elif new_update_id > self.update_id:
            self.update_id = new_update_id
            self.full_orderbook_update(recv["data"])
            self.orderbook.update_book(self.asks, self.bids)
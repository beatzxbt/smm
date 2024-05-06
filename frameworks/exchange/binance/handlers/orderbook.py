import numpy as np
from typing import List, Dict, Union
from frameworks.exchange.base.ws_handlers.orderbook import OrderbookHandler
from frameworks.sharedstate import SharedState

class BinanceOrderbookHandler(OrderbookHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.orderbook)
        self.update_id = 0
    
    def bba_update(self, recv: Dict) -> None:
        """Unused for now"""
        self.orderbook.bba[0, :] = [float(recv["b"]), float(recv["B"])]
        self.orderbook.bba[1, :] = [float(recv["a"]), float(recv["A"])]

    def full_orderbook_update(self, recv: Dict) -> None:
        self.bids = np.array(recv["b"], dtype=np.float64)
        self.asks = np.array(recv["a"], dtype=np.float64)

    def initialize(self, recv: Dict) -> None:
        self.update_id = int(recv["lastUpdateId"])
        self.full_orderbook_update(recv)
        self.orderbook.initialize(self.asks, self.bids)

    def process(self, recv: Dict) -> Dict:
        new_update_id = int(recv["u"])
        if new_update_id > self.update_id:
            self.update_id = new_update_id
            self.full_orderbook_update(recv)
            self.orderbook.update_book(self.asks, self.bids)
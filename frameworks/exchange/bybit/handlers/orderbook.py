import numpy as np
from typing import List, Dict, Union

from frameworks.exchange.base.ws_handlers.orderbook import OrderbookHandler

class BybitOrderbookHandler(OrderbookHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["orderbook"])
        self.update_id = 0
    
    def bba_update(self, recv: Dict) -> None:
        """Unused for now"""
        self.orderbook.bba[0, :] = list(map(float, recv["a"]))
        self.orderbook.bba[1, :] = list(map(float, recv["b"]))

    def full_orderbook_update(self, recv: Dict) -> None:
        if "a" in recv:
            self.bids = np.array(recv["a"], dtype=np.float64)

        if "b" in recv:
            self.asks = np.array(recv["b"], dtype=np.float64)

    def refresh(self, recv: Dict) -> None:
        try:
            self.update_id = int(recv["result"]["u"])
            self.full_orderbook_update(recv["result"])
            self.orderbook.refresh(self.asks, self.bids)

        except Exception as e:
            raise Exception(f"Orderbook Refresh :: {e}")

    def process(self, recv: Dict) -> None:
        try:
            new_update_id = int(recv["data"]["u"])

            if new_update_id == 1:
                self.update_id = new_update_id
                self.full_orderbook_update(recv["data"])
                self.orderbook.refresh(self.asks, self.bids)
            
            elif new_update_id > self.update_id:
                self.update_id = new_update_id
                self.full_orderbook_update(recv["data"])
                self.orderbook.update_book(self.asks, self.bids)

        except Exception as e:
            print(recv)
            raise Exception(f"Orderbook Process :: {e}")

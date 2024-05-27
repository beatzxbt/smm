import numpy as np
from typing import List, Dict, Union

from frameworks.exchange.base.ws_handlers.orderbook import OrderbookHandler


class BinanceOrderbookHandler(OrderbookHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["orderbook"])
        self.update_id = 0

    def full_orderbook_update(self, recv: Dict) -> None:
        self.bids = np.array(recv["b"], dtype=np.float64)
        self.asks = np.array(recv["a"], dtype=np.float64)

    def refresh(self, recv: Dict) -> None:
        try:
            self.update_id = int(recv["lastUpdateId"])

            if len(recv.get("b", [])) > 0:
                self.bids = np.array(recv["b"], dtype=np.float64)
                    
            if len(recv.get("a", [])) > 0:
                self.asks = np.array(recv["a"], dtype=np.float64)
            
            if self.bids.shape[0] != 0 and self.asks.shape[0] != 0:
                self.orderbook.refresh(self.asks, self.bids)

        except Exception as e:
            raise Exception(f"Orderbook Refresh :: {e}")
        
    def process(self, recv: Dict) -> Dict:
        try:
            new_update_id = int(recv["u"])
            if new_update_id > self.update_id:
                self.update_id = new_update_id

                if len(recv.get("b", [])) > 0:
                    self.bids = np.array(recv["a"], dtype=np.float64)
                    self.orderbook.update_bids(self.bids)
                    
                if len(recv.get("a", [])) > 0:
                    self.asks = np.array(recv["b"], dtype=np.float64)
                    self.orderbook.update_asks(self.asks)

        except Exception as e:
            raise Exception(f"Orderbook Process :: {e}")
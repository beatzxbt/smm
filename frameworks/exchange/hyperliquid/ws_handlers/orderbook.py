import numpy as np
from typing import List, Dict, Any

from frameworks.exchange.base.ws_handlers.orderbook import Orderbook, OrderbookHandler

class HyperliquidOrderbookHandler(OrderbookHandler):
    def __init__(self, orderbook: Orderbook) -> None:
        super().__init__(orderbook)
    
    def refresh(self, recv: List[List[Dict]]) -> None:
        try:
            seq_id = 0
            bids = np.array([[float(level["px"]), float(level["sz"])] for level in recv[0]])
            asks = np.array([[float(level["px"]), float(level["sz"])] for level in recv[1]])

            if bids.size != 0 and asks.size != 0:
                self.orderbook.refresh(asks, bids, seq_id)

        except Exception as e:
            raise Exception(f"Orderbook refresh - {e}")

    def process(self, recv: Dict[str, Any]) -> None:
        try:
            data: Dict[str, Any] = recv["data"]

            seq_id = int(data.get("time")) # Use timestamp as a sequence ID
            bids = np.array([[float(level["px"]), float(level["sz"])] for level in data["levels"][0]])
            asks = np.array([[float(level["px"]), float(level["sz"])] for level in data["levels"][1]])

            if bids.size != 0:
                self.orderbook.update_bids(bids, seq_id)
                
            if asks.size != 0:
                self.orderbook.update_asks(asks, seq_id)

        except Exception as e:
            raise Exception(f"Orderbook process - {e}")
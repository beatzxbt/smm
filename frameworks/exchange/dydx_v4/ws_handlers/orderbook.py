import numpy as np
from typing import Dict, Any

from frameworks.exchange.base.ws_handlers.orderbook import Orderbook, OrderbookHandler


class DydxOrderbookHandler(OrderbookHandler):
    def __init__(self, orderbook: Orderbook) -> None:
        super().__init__(orderbook)

    def refresh(self, recv: Dict[str, Any]) -> None:
        try:
            bids = np.array(recv.get("bids"), dtype=np.float64)
            asks = np.array(recv.get("asks"), dtype=np.float64)

            if bids.size != 0 and asks.size != 0:
                self.orderbook.refresh(asks, bids, 0)

        except Exception as e:
            raise Exception(f"Orderbook refresh - {e}")

    def process(self, recv: Dict[str, Any]) -> None:
        try:
            data: Dict[str, Any] = recv["contents"]
            seq_id = int(recv.get("message_id"))

            bids = np.array(data.get("bids"), dtype=np.float64)
            asks = np.array(data.get("asks"), dtype=np.float64)
            
            if seq_id == 1: 
                if bids.size != 0 and asks.size != 0:
                    self.orderbook.refresh(asks, bids, seq_id)

            else:
                if bids.size != 0:
                    self.orderbook.update_bids(bids, seq_id)

                if asks.size != 0:
                    self.orderbook.update_asks(asks, seq_id)

        except Exception as e:
            raise Exception(f"Orderbook process - {e}")

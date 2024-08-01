import numpy as np
from typing import Dict, Any

from frameworks.exchange.base.ws_handlers.orderbook import Orderbook, OrderbookHandler


class BybitOrderbookHandler(OrderbookHandler):
    def __init__(self, orderbook: Orderbook) -> None:
        super().__init__(orderbook)

    def refresh(self, recv: Dict[str, Any]) -> None:
        try:
            data: Dict[str, Any] = recv["result"]

            seq_id = int(data.get("u"))
            bids = np.array(data.get("b"), dtype=np.float64)
            asks = np.array(data.get("a"), dtype=np.float64)

            self.orderbook.refresh(asks, bids, seq_id)

        except Exception as e:
            raise Exception(f"Orderbook refresh - {e}")

    def process(self, recv: Dict[str, Any]) -> None:
        try:
            data: Dict[str, Any] = recv["data"]
            seq_id = int(recv.get("u"))
            update_type = recv["type"]

            bids = np.array(data.get("b"), dtype=np.float64)
            asks = np.array(data.get("a"), dtype=np.float64)
            
            if seq_id == 1 or update_type == "snapshot":
                self.orderbook.refresh(asks, bids, seq_id)

            elif update_type == "delta":
                if bids.size != 0:
                    self.orderbook.update_bids(bids, seq_id)

                if asks.size != 0:
                    self.orderbook.update_asks(asks, seq_id)

        except Exception as e:
            raise Exception(f"Orderbook process - {e}")

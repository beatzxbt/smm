import numpy as np
from typing import Dict

from frameworks.exchange.base.ws_handlers.orderbook import OrderbookHandler


class BybitOrderbookHandler(OrderbookHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["orderbook"])
        self.update_id = 0

    def refresh(self, recv: Dict) -> None:
        try:
            data = recv["result"]

            self.update_id = int(data["u"])
            self.bids = np.array(data["b"], dtype=np.float64)
            self.asks = np.array(data["a"], dtype=np.float64)

            if self.bids.shape[0] != 0 and self.asks.shape[0] != 0:
                self.orderbook.refresh(self.asks, self.bids)

        except Exception as e:
            raise Exception(f"[Orderbook refresh] {e}")

    def process(self, recv: Dict) -> None:
        try:
            data = recv["data"]
            new_update_id = int(data["u"])
            update_type = recv["type"]

            if new_update_id == 1 or update_type == "snapshot":
                self.update_id = new_update_id
                self.bids = np.array(data["b"], dtype=np.float64)
                self.asks = np.array(data["a"], dtype=np.float64)
                self.orderbook.refresh(self.asks, self.bids)

            elif new_update_id > self.update_id:
                self.update_id = new_update_id

                if len(data.get("b", [])) > 0:
                    self.bids = np.array(data["b"], dtype=np.float64)
                    self.orderbook.update_bids(self.bids)

                if len(data.get("a", [])) > 0:
                    self.asks = np.array(data["a"], dtype=np.float64)
                    self.orderbook.update_asks(self.asks)

        except Exception as e:
            raise Exception(f"[Orderbook process] {e}")

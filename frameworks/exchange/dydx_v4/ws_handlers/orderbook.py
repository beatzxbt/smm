import numpy as np
from typing import Dict

from frameworks.exchange.base.ws_handlers.orderbook import OrderbookHandler


class DydxOrderbookHandler(OrderbookHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["orderbook"])
        self.update_id = 0

    def refresh(self, recv: Dict) -> None:
        try:
            bids = np.array(recv["bids"], dtype=np.float64)
            asks = np.array(recv["asks"], dtype=np.float64)

            if bids.shape[0] != 0 and asks.shape[0] != 0:
                self.orderbook.refresh(asks, bids)
 
        except Exception as e:
            raise Exception(f"Orderbook refresh - {e}")

    def process(self, recv: Dict) -> None:
        try:
            data = recv["contents"]
            new_update_id = int(data["message_id"])

            if new_update_id == 1:
                self.update_id = new_update_id

                bids = np.array(recv["bids"], dtype=np.float64)
                asks = np.array(recv["asks"], dtype=np.float64)

                if bids.shape[0] != 0 and asks.shape[0] != 0:
                    self.orderbook.refresh(asks, bids)

            elif new_update_id > self.update_id:
                self.update_id = new_update_id

                bids = np.array(recv["bids"], dtype=np.float64)
                asks = np.array(recv["asks"], dtype=np.float64)

                if bids.shape[0] != 0:
                    self.orderbook.update_bids(bids=bids)

                if asks.shape[0] != 0:
                    self.orderbook.update_asks(asks=asks)

        except Exception as e:
            raise Exception(f"Orderbook process - {e}")

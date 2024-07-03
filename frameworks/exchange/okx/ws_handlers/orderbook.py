import numpy as np
from typing import Dict

from frameworks.exchange.base.ws_handlers.orderbook import OrderbookHandler


class OkxOrderbookHandler(OrderbookHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["orderbook"])
        self.update_id = 0

    def refresh(self, recv: Dict) -> None:
        try:
            data = recv["data"]

            self.orderbook.refresh(
                asks=np.array(data["asks"], dtype=np.float64)[:, :2], 
                bids=np.array(data["bids"], dtype=np.float64)[:, :2]
            )

        except Exception as e:
            raise Exception(f"[Orderbook refresh] {e}")

    def process(self, recv: Dict) -> None:
        try:
            data = recv["data"][0]
            update_type = recv["action"]
            new_seq_id = data["seqId"]
            prev_seq_id = data["prevSeqId"]

            if prev_seq_id == -1 or update_type == "snapshot":
                self.update_id = new_seq_id
                bids = np.array(data["bids"], dtype=np.float64)[:, :2]
                asks = np.array(data["asks"], dtype=np.float64)[:, :2]
                self.orderbook.refresh(asks, bids)

            elif new_seq_id > self.update_id:
                if prev_seq_id != self.update_id:
                    raise Exception("Sequence ID mismatch. Data might be lost or out of order.")
                
                self.update_id = new_seq_id

                if len(data.get("bids", [])) > 0:
                    bids = np.array(data["bids"], dtype=np.float64)[:, :2]
                    self.orderbook.update_bids(bids)

                if len(data.get("asks", [])) > 0:
                    asks = np.array(data["asks"], dtype=np.float64)[:, :2]
                    self.orderbook.update_asks(asks)

            elif new_seq_id < self.update_id:
                self.update_id = new_seq_id

            elif new_seq_id == self.update_id and prev_seq_id == self.update_id:
                pass

        except Exception as e:
            raise Exception(f"[Orderbook process] {e}")

import numpy as np
from typing import Dict

from frameworks.exchange.base.ws_handlers.orderbook import Orderbook, OrderbookHandler


class BinanceOrderbookHandler(OrderbookHandler):
    def __init__(self, orderbook: Orderbook) -> None:
        super().__init__(orderbook)

    def refresh(self, recv: Dict) -> None:
        try:
            seq_id = int(recv.get("lastUpdateId"))
            bids = np.array(recv.get("bids"), dtype=np.float64)
            asks = np.array(recv.get("asks"), dtype=np.float64)

            self.orderbook.refresh(asks, bids, seq_id)

        except Exception as e:
            raise Exception(f"Orderbook refresh - {e}")

    def process(self, recv: Dict) -> None:
        try:
            seq_id = int(recv.get("u"))
 
            if recv.get("b", []):
                bids = np.array(recv["b"], dtype=np.float64)
                self.orderbook.update_bids(bids, seq_id)

            if recv.get("a", []):
                asks = np.array(recv["a"], dtype=np.float64)
                self.orderbook.update_asks(asks, seq_id)

        except Exception as e:
            raise Exception(f"Orderbook process - {e}")

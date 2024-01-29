import numpy as np
from typing import Dict

class HyperliquidOrderbookHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market

    def process(self, recv: Dict) -> Dict:
        bids = np.array([[level["px"], level["sz"]] for level in recv["levels"][0]], dtype=np.float64)
        asks = np.array([[level["px"], level["sz"]] for level in recv["levels"][1]], dtype=np.float64)

        self.market[recv["s"]]["book"].update(
            asks=asks,
            bids=bids,
            timestamp=float(recv["time"])
        )
import numpy as np
from typing import List, Dict, Union

class BinanceOrderbookHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market

    def process(self, recv: Dict) -> Dict:
        self.market[recv["s"]]["book"].update(
            asks=np.array(recv["data"]["a"], dtype=np.float64),
            bids=np.array(recv["data"]["b"], dtype=np.float64),
            timestamp=float(recv["T"])
        )
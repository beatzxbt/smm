import numpy as np
from typing import List, Dict, Union

class BinanceBbaHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market
        self._bids_cache_ = np.array([0.0, 0.0], dtype=np.float64)
        self._asks_cache_ = np.array([0.0, 0.0], dtype=np.float64)

    def process(self, recv: Union[Dict, List, str]) -> Dict:
        self._bids_cache_[0] = float(recv["data"]["b"])
        self._bids_cache_[1] = float(recv["data"]["B"])
        self._asks_cache_[0] = float(recv["data"]["a"])
        self._asks_cache_[1] = float(recv["data"]["A"])

        self.market[recv["s"]]["book"].update(
            asks=self._asks_cache_.copy(),
            bids=self._bids_cache_.copy(),
            timestamp=float(recv["T"])
        )

from typing import List, Dict, Union

class BinanceOrderbookHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market
        self.book_pointer = None

    def process(self, recv: Union[Dict, List, str]) -> Dict:
        if self.book_pointer is None:
            self.book_pointer = self.market[recv["data"]["s"]]["book"]

        self.book_pointer.update(
            asks=recv["data"]["a"],
            bids=recv["data"]["b"],
            timestamp=float(recv["ts"])
        )
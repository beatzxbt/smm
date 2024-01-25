from typing import List, Dict, Union

class CcxtOrderbookHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market

    def process(self, recv: Union[Dict, List, str]) -> Dict:
        self.market[recv["s"]]["book"].update(
            asks=recv["data"]["a"],
            bids=recv["data"]["b"]
        )
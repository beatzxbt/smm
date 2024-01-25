from typing import List, Dict, Union

class CcxtBbaHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market

    def process(self, recv: Union[Dict, List, str]) -> Dict:
        self.market[recv["s"]]["bba"][0, 0] = float(recv["data"]["b"])
        self.market[recv["s"]]["bba"][0, 1] = float(recv["data"]["B"])
        self.market[recv["s"]]["bba"][1, 0] = float(recv["data"]["a"])
        self.market[recv["s"]]["bba"][1, 1] = float(recv["data"]["A"])
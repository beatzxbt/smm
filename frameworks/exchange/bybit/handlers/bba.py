from typing import List, Dict, Union

class BybitBbaHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market
        self.bba_pointer = None

    def process(self, recv: Union[Dict, List, str]) -> Dict:
        if self.bba_pointer is None:
            self.bba_pointer = self.market[recv["data"]["s"]]["bba"]
            
        self.bba_pointer[0, 0] = float(recv["data"]["b"][0])
        self.bba_pointer[0, 1] = float(recv["data"]["b"][1])
        self.bba_pointer[1, 0] = float(recv["data"]["a"][0])
        self.bba_pointer[1, 1] = float(recv["data"]["a"][1])
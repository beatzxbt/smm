from typing import Dict

class BinanceTickerHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market

    def process(self, recv: Dict) -> Dict:
        self.market[recv["s"]]["24hVol"] = float(recv["data"]["v"])
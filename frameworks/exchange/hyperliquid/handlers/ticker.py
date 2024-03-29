from typing import Dict

class BinanceTickerHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market

    def process(self, recv: Dict) -> Dict:
        self.market[recv["s"]]["markPrice"] = float(recv["data"]["p"])
        self.market[recv["s"]]["indexPrice"] = float(recv["data"]["i"])
        self.market[recv["s"]]["fundingRate"] = float(recv["data"]["r"])
        self.market[recv["s"]]["fundingTimestamp"] = float(recv["data"]["T"])
        # self.market[recv["s"]]["24hVol"] = None # TODO: Requires mini-ticker stream
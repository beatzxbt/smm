from typing import Dict

class BinanceTickerHandler:
    def __init__(self, market: Dict) -> None:
        self.market = market
        self.ticker_pointer = None

    def process(self, recv: Dict) -> Dict:
        if self.ticker_pointer is None:
            self.ticker_pointer = self.market[recv["symbol"]]

        self.ticker_pointer["markPrice"] = float(recv["data"]["markPrice"])
        self.ticker_pointer["indexPrice"] = float(recv["data"]["indexPrice"])
        self.ticker_pointer["fundingRate"] = float(recv["data"]["fundingRate"])
        self.ticker_pointer["fundingTimestamp"] = float(recv["data"]["nextFundingTime"])
        self.ticker_pointer["24hVol"] = float(recv["data"]["volume24h"])
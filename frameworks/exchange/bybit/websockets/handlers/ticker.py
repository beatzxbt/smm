
import json
from frameworks.sharedstate.market import MarketDataSharedState


class BybitTickerHandler:


    def __init__(self, sharedstate: MarketDataSharedState, symbol: str) -> None:
        self.bybit = sharedstate.bybit[symbol]


    def update(self, recv: json) -> None:
        if "markPrice" in recv["data"]:
            self.bybit["mark_price"] = float(recv["data"]["markPrice"])

        if "indexPrice" in recv["data"]:
            self.bybit["index_price"] = float(recv["data"]["indexPrice"])

        if "lastPrice" in recv["data"]:
            self.bybit["last_price"] = float(recv["data"]["lastPrice"])

        if "fundingRate" in recv["data"]:
            self.bybit["funding_rate"] = float(recv["data"]["fundingRate"])

        if "volume24h" in recv["data"]:
            self.bybit["volume_24h"] = float(recv["data"]["volume24h"])
            
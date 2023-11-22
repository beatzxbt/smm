
import json
from frameworks.sharedstate.market import MarketDataSharedState


class HyperLiquidTickerHandler:


    def __init__(self, sharedstate: MarketDataSharedState, symbol: str) -> None:
        self.hlq = sharedstate.hyperliquid[symbol]


    def update(self, recv: json) -> None:
        if "markPrice" in recv["data"]:
            self.hlq["mark_price"] = float(recv["data"]["markPrice"])

        if "indexPrice" in recv["data"]:
            self.hlq["index_price"] = float(recv["data"]["indexPrice"])

        if "lastPrice" in recv["data"]:
            self.hlq["last_price"] = float(recv["data"]["lastPrice"])

        if "fundingRate" in recv["data"]:
            self.hlq["funding_rate"] = float(recv["data"]["fundingRate"])

        if "volume24h" in recv["data"]:
            self.hlq["volume_24h"] = float(recv["data"]["volume24h"])
            
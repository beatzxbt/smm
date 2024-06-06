from typing import Dict

from frameworks.exchange.base.ws_handlers.ticker import TickerHandler


class BinanceTickerHandler(TickerHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["ticker"])

    def refresh(self, recv: Dict) -> None:
        try:
            self.format["markPrice"] = float(
                recv.get("markPrice", self.format["markPrice"])
            )
            self.format["indexPrice"] = float(
                recv.get("indexPrice", self.format["indexPrice"])
            )
            self.format["fundingRate"] = float(
                recv.get("lastFundingRate", self.format["fundingRate"])
            )
            self.format["fundingTime"] = float(
                recv.get("nextFundingTime", self.format["fundingTime"])
            )
            self.ticker.update(self.format)

        except Exception as e:
            raise Exception(f"Ticker Refresh :: {e}")

    def process(self, recv: Dict) -> None:
        try:
            self.format["markPrice"] = float(recv.get("p", self.format["markPrice"]))
            self.format["indexPrice"] = float(recv.get("i", self.format["indexPrice"]))
            self.format["fundingRate"] = float(
                recv.get("r", self.format["fundingRate"])
            )
            self.format["fundingTime"] = float(
                recv.get("T", self.format["fundingTime"])
            )
            self.ticker.update(self.format)

        except Exception as e:
            raise Exception(f"Ticker Process :: {e}")

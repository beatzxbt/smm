from typing import Dict

from frameworks.exchange.base.ws_handlers.ticker import TickerHandler


class BybitTickerHandler(TickerHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["ticker"])

    def refresh(self, recv: Dict) -> None:
        try:
            for ticker in recv["result"]["list"]:
                self.format["markPrice"] = float(
                    ticker.get("markPrice", self.format["markPrice"])
                )
                self.format["indexPrice"] = float(
                    ticker.get("indexPrice", self.format["indexPrice"])
                )
                self.format["fundingRate"] = float(
                    ticker.get("fundingRate", self.format["fundingRate"])
                )
                self.format["fundingTime"] = float(
                    ticker.get("nextFundingTime", self.format["fundingTime"])
                )
                self.ticker.update(self.format)

        except Exception as e:
            raise Exception(f"Ticker Refresh :: {e}")

    def process(self, recv: Dict) -> None:
        try:
            self.format["markPrice"] = float(
                recv["data"].get("markPrice", self.format["markPrice"])
            )
            self.format["indexPrice"] = float(
                recv["data"].get("indexPrice", self.format["indexPrice"])
            )
            self.format["fundingRate"] = float(
                recv["data"].get("fundingRate", self.format["fundingRate"])
            )
            self.format["fundingTime"] = float(
                recv["data"].get("nextFundingTime", self.format["fundingTime"])
            )
            self.ticker.update(self.format)

        except Exception as e:
            raise Exception(f"Ticker Process :: {e}")

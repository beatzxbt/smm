from typing import Dict

from frameworks.exchange.base.ws_handlers.ticker import TickerHandler


class OkxTickerHandler(TickerHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["ticker"])

    def refresh(self, recv: Dict) -> None:
        try:
            data = recv["data"][0]

            self.format["markPrice"] = float(
                data.get("markPx", self.format["markPrice"])
            )
            self.format["indexPrice"] = float(
                data.get("idxPx", self.format["indexPrice"])
            )
            self.format["fundingRate"] = float(
                data.get("fundingRate", self.format["fundingRate"])
            )
            self.format["fundingTime"] = float(
                data.get("fundingTime", self.format["fundingTime"])
            )
            self.ticker.update(self.format)

        except Exception as e:
            raise Exception(f"[Ticker refresh] {e}")

    def process(self, recv: Dict) -> None:
        try:
            data = recv["data"][0]

            self.format["markPrice"] = float(
                data.get("markPx", self.format["markPrice"])
            )
            self.format["indexPrice"] = float(
                data.get("idxPx", self.format["indexPrice"])
            )
            self.format["fundingRate"] = float(
                data.get("fundingRate", self.format["fundingRate"])
            )
            self.format["fundingTime"] = float(
                data.get("fundingTime", self.format["fundingTime"])
            )
            self.ticker.update(self.format)

        except Exception as e:
            raise Exception(f"[Ticker process] {e}")

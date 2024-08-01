from typing import Dict

from frameworks.exchange.base.ws_handlers.ticker import Ticker, TickerHandler


class BybitTickerHandler(TickerHandler):
    def __init__(self, ticker: Ticker) -> None:
        super().__init__(ticker=ticker)

    def refresh(self, recv: Dict) -> None:
        try:
            self.ticker.update(
                fundingTs=float(recv.get("nextFundingTime", self.ticker.fundingTs)),
                fundingRate=float(recv.get("fundingRate", self.ticker.fundingRate)),
                markPrice=float(recv.get("markPrice", self.ticker.markPrice)),
                indexPrice=float(recv.get("indexPrice", self.ticker.indexPrice)),
            )

        except Exception as e:
            raise Exception(f"Ticker refresh - {e}")

    def process(self, recv: Dict) -> None:
        try:
            self.ticker.update(
                fundingTs=float(recv.get("nextFundingTime", self.ticker.fundingTs)),
                fundingRate=float(recv.get("fundingRate", self.ticker.fundingRate)),
                markPrice=float(recv.get("markPrice", self.ticker.markPrice)),
                indexPrice=float(recv.get("indexPrice", self.ticker.indexPrice)),
            )

        except Exception as e:
            raise Exception(f"Ticker process - {e}")


from typing import List, Dict, Any
from datetime import datetime, timedelta

from frameworks.exchange.base.ws_handlers.ticker import Ticker, TickerHandler


class HyperliquidTickerHandler(TickerHandler):
    def __init__(self, ticker: Ticker) -> None:
        super().__init__(ticker=ticker)
    
    def time_to_funding_ms(self) -> float:
        current_timestamp = datetime.now()
        current_hour = current_timestamp.replace(microsecond=0, second=0, minute=0)
        next_hour = current_hour + timedelta(hours=1)
        return (next_hour.timestamp() - current_timestamp.timestamp()) * 1000.0
    
    def refresh(self, recv) -> None:
        pass
    
    def process(self, recv: Dict[str, Any]) -> None:
        try:
            data: Dict[str, Any] = recv["data"]["ctx"]

            self.ticker.update(
                fundingTs=self.time_to_funding_ms(),
                fundingRate=float(data.get("funding", self.ticker.fundingRate)),
                markPrice=float(data.get("markPx", self.ticker.markPrice)),
                indexPrice=float(data.get("oraclePx", self.ticker.indexPrice)),
            )

        except Exception as e:
            raise Exception(f"Ticker process - {e}")

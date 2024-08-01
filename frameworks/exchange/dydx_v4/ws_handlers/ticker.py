from time import time, gmtime
from typing import Dict, Any

from frameworks.exchange.base.ws_handlers.ticker import Ticker, TickerHandler


class DydxTickerHandler(TickerHandler):
    def __init__(self, ticker: Ticker, symbol: str) -> None:
        super().__init__(ticker=ticker)
        self.symbol = symbol

    def nearest_funding_time(self) -> int:
        """
        Calculates the nearest funding settlement time in Unix timestamp format (UTC).

        The nearest funding settlement times are at 8:00 AM, 4:00 PM, or 12:00 AM (midnight) UTC.

        Steps
        -----
        1. Get the current Unix timestamp using `time()`.
        2. Convert the current Unix timestamp to UTC time using `gmtime(now)`.
        3. Calculate the current time in seconds since midnight (UTC) using the current hour, minute, and second.
        4. Define the target settlement times (8:00 AM, 4:00 PM, and 12:00 AM) in seconds since midnight (UTC).
        5. Compute the differences between the current time and each target time. Use modulo 86400 to ensure positive values and wrap around the next day if needed.
        6. Find the smallest positive difference, which represents the nearest target time.
        7. Add this difference to the current Unix timestamp to get the nearest target settlement time in Unix timestamp format.
        8. Return the nearest target settlement time as an integer Unix timestamp.

        Returns
        -------
        int
            The Unix timestamp of the nearest funding settlement time (8:00 AM, 4:00 PM, or 12:00 AM) in UTC.
        """
        now = time()
        current_time = gmtime(now) 
        current_hour = current_time.tm_hour
        current_minute = current_time.tm_min
        seconds_since_midnight = current_hour * 3600 + current_minute * 60 + current_time.tm_sec
        target_times = [8 * 3600, 16 * 3600, 0]  # 8:00 AM, 4:00 PM, 12:00 AM
        differences = [(target - seconds_since_midnight) % 86400 for target in target_times]
        nearest_timestamp = now + min(differences)
        return nearest_timestamp

    def refresh(self, recv: Dict[str, Dict]) -> None:
        try:
            data: Dict = recv["markets"].get(self.symbol)

            self.ticker.update(
                fundingTs=self.nearest_funding_time(),
                fundingRate=float(data.get("nextFundingRate", self.ticker.fundingRate)),
                markPrice=float(data.get("oraclePrice", self.ticker.markPrice)),
                indexPrice=float(data.get("oraclePrice", self.ticker.indexPrice)),
            )

        except Exception as e:
            raise Exception(f"Ticker refresh - {e}")

    def process(self, recv: Dict[str, Any]) -> None:
        try:
            self.ticker.update(
                fundingTs=self.nearest_funding_time(),
                fundingRate=float(recv.get("nextFundingRate", self.ticker.fundingRate)),
                markPrice=float(recv.get("oraclePrice", self.ticker.markPrice)),
                indexPrice=float(recv.get("oraclePrice", self.ticker.indexPrice)),
            )

        except Exception as e:
            raise Exception(f"Ticker process - {e}")


from typing import List, Dict
from datetime import datetime, timedelta

from frameworks.exchange.base.ws_handlers.ticker import TickerHandler
from frameworks.sharedstate import SharedState

def get_next_round_hour_timestamp() -> float:
    now = datetime.now()
    next_hour = now.replace(microsecond=0, second=0, minute=0) + timedelta(hours=1)
    return next_hour.timestamp()

class HyperliquidTickerHandler(TickerHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.ticker)

        self.asset_idx = 0
        self.asset_found = False
    
    def time_to_funding_ms(self) -> float:
        expiry_time = get_next_round_hour_timestamp()
        now = datetime.now().timestamp()
        return (expiry_time - now) * 1000
    
    def refresh(self, recv: List[Dict]) -> None:
        pass
    
    def process(self, recv: Dict) -> None:
        if not self.asset_found:
            for asset in recv["meta"]["universe"]:
                if asset["name"] == self.ss.symbol:
                    self.asset_found = True
                    break

                self.asset_idx += 1

        asset_ctx = recv["assetCtxs"][self.asset_idx]
        self.format["markPrice"] = float(asset_ctx["markPx"])
        self.format["indexPrice"] = float(asset_ctx["oraclePx"])
        self.format["fundingTime"] = self.time_to_funding_ms()
        self.format["fundingRate"] = float(asset_ctx["funding"])
        self.ticker.update(self.format)
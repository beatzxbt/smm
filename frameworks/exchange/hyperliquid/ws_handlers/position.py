from typing import List, Dict

from frameworks.exchange.base.ws_handlers.position import PositionHandler
from frameworks.sharedstate import SharedState

class HyperliquidPositionHandler(PositionHandler):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        super().__init__(self.ss.current_position)

        self.asset_idx = 0
        self.asset_found = False
    
    def refresh(self, recv: List[Dict]) -> None:
        for position in recv["assetPositions"]:
            if position["coin"] != self.ss.symbol:
                continue

            self.position["price"] = float(position["entryPx"])
            self.position["size"] = float(position["szi"])
            self.position["uPnL"] = float(position["unrealizedPnl"])
            self.current_position.update(self.position)

    def process(self, recv: Dict) -> None:
        self.ss.account_balance = float(recv["clearinghouseState"]["marginSummary"]["accountValue"])

        if not self.asset_found:
            for asset in recv["meta"]["universe"]:
                if asset["name"] == self.ss.symbol:
                    self.asset_found = True
                    break
                
                self.asset_idx += 1
        
        position = recv["clearinghouseState"]["assetPositions"][self.asset_idx]["position"]
        self.position["price"] = float(position["entryPx"])
        self.position["size"] = float(position["szi"])
        self.position["uPnL"] = float(position["unrealizedPnl"])
        self.current_position.update(self.position)

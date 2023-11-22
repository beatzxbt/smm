
from frameworks.sharedstate.private import PrivateDataSharedState


class HyperLiquidPositionHandler:


    def __init__(
        self, 
        sharedstate: PrivateDataSharedState, 
        symbol: str
    ) -> None:
    
        self.pdss = sharedstate
        self.symbol = symbol
        self.hlq = self.pdss.hyperliquid[self.symbol]["Data"]

    
    def sync(self, recv: dict) -> None:
        self.process(recv["result"]["list"][0])


    def update(self, data: list) -> None:
        if data["side"]:
            self.hlq["position_size"] = float(data["size"]) if data["side"] == "Buy" else -float(data["size"]) 
            self.hlq["leverage"] = float(data["leverage"])
            self.hlq["unrealized_pnl"] = float(data["unrealisedPnl"])



from frameworks.sharedstate.private import PrivateDataSharedState


class BybitPositionHandler:


    def __init__(self, sharedstate: PrivateDataSharedState, symbol: str) -> None:
        self.pdss = sharedstate
        self.symbol = symbol
        self.bybit = self.pdss.bybit[self.symbol]["Data"]

    
    def sync(self, recv: dict) -> None:
        self.process(recv["result"]["list"][0])


    def process(self, data: list) -> None:
        side = data["side"]

        if side:
            self.bybit["position_size"] = float(data["size"]) if side == "Buy" else -float(data["size"]) 
            self.bybit["leverage"] = float(data["leverage"])
            self.bybit["unrealized_pnl"] = float(data["unrealisedPnl"])


from frameworks.sharedstate.private import PrivateDataSharedState


class BybitWalletHandler:


    def __init__(self, sharedstate: PrivateDataSharedState, symbol: str) -> None:
        self.pdss = sharedstate
        self.symbol = symbol
        self.bybit_api = self.pdss.bybit["API"]

    
    def sync(self, recv: dict) -> None:
        self.process(recv["result"]["list"][0])


    def update(self, data: list) -> None:
        self.bybit_api["account_balance"] = float(data["totalWalletBalance"])
        self.bybit_api["maintainance_margin"] = float(data["totalMaintenanceMargin"])

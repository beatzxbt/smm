
from frameworks.tools.logger import Logger
from frameworks.sharedstate.private import PrivateDataSharedState


class CalculateInventory:
    

    def __init__(
        self, 
        pdss: PrivateDataSharedState
    ) -> None:

        self.pdss = pdss
        self.logging = Logger()


    def position_delta(
        self
    ) -> None:
        """
        Calculates the current position delta relative to account size
        """
        
        balance = self.pdss.bybit["API"]["account_balance"]
        leverage = self.pdss.bybit["Data"][symbol]["leverage"]
        size = self.pdss.bybit["Data"][symbol]["position_size"]

        account_max = (balance * leverage) / 2.05

        return (size/account_max) if size > 0 else -(size/account_max)

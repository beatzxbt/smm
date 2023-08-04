
from src.strategy.inventory import Inventory


class BybitPositionHandler:


    def __init__(self, sharedstate, data: list) -> None:
        self.ss = sharedstate
        self.data = data

    
    def process(self):
        """
        Add TWAP logic here, just enough to get it below limits \n
        Add checker so many TWAPs dont activate accidentally! \n
        """
        
        Inventory(self.ss).calculate_delta(self.data)

        
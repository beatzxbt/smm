
from src.strategy.inventory import Inventory
from src.sharedstate import SharedState


class BybitPositionHandler:


    def __init__(self, sharedstate: SharedState, data: list) -> None:
        self.ss = sharedstate
        self.data = data

    
    def process(self):
        """
        Add TWAP logic here, just enough to get it below limits \n
        Add checker so many TWAPs dont activate accidentally! \n
        """
        
        Inventory(self.ss).calculate_delta(self.data)

        
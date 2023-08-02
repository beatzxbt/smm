import json

from src.strategy.inventory import Inventory


class BybitPositionHandler:


    def __init__(self, sharedstate, data: json) -> None:
        self.ss = sharedstate
        self.data = data

        self.inventory_delta = self.ss.inventory_delta

    
    def process(self):
        """
        Add TWAP logic here, just enough to get it below limits \n
        Add checker so many TWAPs dont activate accidentally! \n
        """
        
        self.inventory_delta = Inventory(self.ss).calculate_delta()

        
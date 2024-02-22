from typing import Dict, List, Union
from src.strategy.inventory import Inventory
from src.sharedstate import SharedState


class BybitPositionHandler:
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.inventory = Inventory(self.ss)
    
    def sync(self, recv: Dict) -> None:
        self.process(recv["result"]["list"][0])

    def process(self, data: Union[Dict, List]) -> None:
        if isinstance(data, list):
            data = data[0]

        if data["side"]:
            value = float(data["positionValue"])
            leverage = float(data["leverage"])
            self.inventory.position_delta(data["side"], value, leverage)
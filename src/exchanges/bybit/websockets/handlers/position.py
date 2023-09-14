
from src.strategy.inventory import Inventory
from src.sharedstate import SharedState


class BybitPositionHandler:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate

    
    def sync(self, recv: dict) -> None:
        data = recv["result"]["list"][0]
        self.process(data)


    def process(self, data: list) -> None:
        side = data["side"]
        
        if len(side) != 0:
            value = float(data["positionValue"])
            leverage = float(data["leverage"])

            Inventory(self.ss).position_delta(side, value, leverage)

        
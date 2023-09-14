
from src.sharedstate import SharedState


class BybitTickerHandler:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    def process(self, recv) -> None:
        data = recv["data"]

        if "markPrice" in data:
            self.ss.bybit_mark_price = float(data["markPrice"])
            
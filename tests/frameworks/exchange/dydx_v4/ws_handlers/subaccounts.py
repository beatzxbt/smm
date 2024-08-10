from typing import List, Dict

from frameworks.exchange.dydx_v4.ws_handlers.orders import DydxOrdersHandler
from frameworks.exchange.dydx_v4.ws_handlers.position import DydxPositionHandler


class DydxSubaccountsHandler:
    def __init__(self, data: Dict) -> None:
        self.data = data

        self.orders = DydxOrdersHandler(self.data)
        self.position = DydxPositionHandler(self.data)
    
    def refresh(self, recv: List[Dict]) -> None:
        self.orders.refresh(recv)
        self.position.refresh(recv)
    
    def process(self, recv: Dict) -> None:
        self.orders.process(recv)
        self.position.process(recv)
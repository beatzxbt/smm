from typing import List, Dict, Any

from frameworks.exchange.dydx_v4.ws_handlers.orders import DydxOrdersHandler
from frameworks.exchange.dydx_v4.ws_handlers.position import DydxPositionHandler


class DydxSubaccountsHandler:
    def __init__(self, data: Dict[str, Any]) -> None:
        self.orders = DydxOrdersHandler(data["orders"])
        self.position = DydxPositionHandler(data["position"])
    
    def refresh(self, recv: List[Dict]) -> None:
        self.orders.refresh(recv)
        self.position.refresh(recv)
    
    def process(self, recv: Dict) -> None:
        self.orders.process(recv)
        self.position.process(recv)
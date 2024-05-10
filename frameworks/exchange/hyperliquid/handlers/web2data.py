from typing import List, Dict

from frameworks.sharedstate import SharedState
from frameworks.exchange.hyperliquid.handlers.ticker import HyperliquidTickerHandler
from frameworks.exchange.hyperliquid.handlers.position import HyperliquidPositionHandler
from frameworks.exchange.hyperliquid.handlers.orders import HyperliquidOrdersHandler

class HyperliquidWeb2DataHandler:
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss

        self.ticker = HyperliquidTickerHandler(self.ss)
        self.position = HyperliquidPositionHandler(self.ss)
    
    def refresh(self, recv: List[Dict]) -> None:
        pass
    
    def process(self, recv: Dict) -> None:
        self.ticker.process(recv)
        self.position.process(recv)
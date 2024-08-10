from typing import List, Dict, Any

from frameworks.exchange.hyperliquid.ws_handlers.ticker import HyperliquidTickerHandler
from frameworks.exchange.hyperliquid.ws_handlers.position import HyperliquidPositionHandler

class HyperliquidWeb2DataHandler:
    def __init__(self, data: Dict[str, Any]) -> None:
        self.ticker = HyperliquidTickerHandler(data["ticker"])
        self.position = HyperliquidPositionHandler(data["position"])
    
    def refresh(self, recv: Dict) -> None:
        self.ticker.refresh(recv)
        self.position.refresh(recv)
    
    def process(self, recv: Dict) -> None:
        self.ticker.process(recv)
        self.position.process(recv)
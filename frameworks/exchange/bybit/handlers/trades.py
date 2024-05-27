from typing import List, Dict

from frameworks.exchange.base.ws_handlers.trades import TradesHandler
from frameworks.exchange.bybit.types import BybitSideConverter

class BybitTradesHandler(TradesHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["trades"])
    
    def refresh(self, recv: List[Dict]) -> None:
        try:
            for trade in recv["result"]["list"]:
                self.format[0] = float(trade["time"])
                self.format[1] = BybitSideConverter.to_num(trade["side"])
                self.format[2] = float(trade["price"])
                self.format[3] = float(trade["size"])
                self.trades.append(self.format.copy())
        
        except Exception as e:
            raise Exception(f"Trades Refresh :: {e}")
    
    def process(self, recv: Dict) -> None: 
        try:
            for trade in recv["data"]:
                self.format[0] = float(trade["T"])
                self.format[1] = BybitSideConverter.to_num(trade["S"])
                self.format[2] = float(trade["p"])
                self.format[3] = float(trade["v"])
                self.trades.append(self.format.copy())

        except Exception as e:
            raise Exception(f"Trades Process :: {e}")
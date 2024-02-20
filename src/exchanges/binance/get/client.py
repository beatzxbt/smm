from binance.client import Client
from typing import Dict
from src.sharedstate import SharedState

class BinancePublicGet:
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.symbol: str = self.ss.binance_symbol
        self.client = Client()

    async def orderbook(self, limit: int) -> Dict:
        return self.client.get_order_book(
            symbol=self.symbol, 
            limit=limit
        )

    async def klines(self, limit: int, interval: int) -> Dict:
        return self.client.get_klines(
            symbol=self.symbol, 
            interval=interval, 
            limit=limit
        )

    async def trades(self, limit: int) -> Dict:
        return self.client.get_recent_trades(
            symbol=self.symbol, 
            limit=limit
        )
    
    async def instrument_info(self) -> Dict:
        return self.client.get_symbol_info(
            symbol=self.symbol
        )
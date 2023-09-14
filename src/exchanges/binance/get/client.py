
from binance.client import Client
from src.sharedstate import SharedState


class BinancePublicGet:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.symbol = self.ss.binance_symbol
        self.client = Client()


    async def orderbook_snapshot(self, limit: int) -> dict:
        return self.client.get_order_book(
            symbol=self.symbol, 
            limit=limit
        )


    async def klines_snapshot(self, limit: int, interval: int) -> dict:
        return self.client.get_klines(
            symbol=self.symbol, 
            interval=interval, 
            limit=limit
        )


    async def trades_snapshot(self, limit: int) -> dict:
        return self.client.get_recent_trades(
            symbol=self.symbol, 
            limit=limit
        )
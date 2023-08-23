
from binance.client import Client


class PublicClient:


    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate
        self.symbol = self.ss.binance_symbol
        self.client = Client()
             

    async def orderbook_snapshot(self, limit):
        
        data = self.client.get_order_book(
            symbol=self.symbol, 
            limit=limit
        )

        return data

    
    async def klines_snapshot(self, limit, interval):
                    
        data = self.client.get_klines(
            symbol=self.symbol,
            interval=interval, 
            limit=limit
        )

        return data

    
    async def trades_snapshot(self, limit):
                    
        data = self.client.get_recent_trades(
            symbol=self.symbol,
            limit=limit
        )

        return data

from binance.client import Client


class BinancePublicGet:


    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self._session = None


    @property
    def session(self):
        if self._session is None:
            self._session = Client()
                
        return self._session


    async def orderbook(self, limit: int) -> dict:
        return self.session.get_order_book(
            symbol=self.symbol, 
            limit=limit
        )


    async def klines(self, limit: int, interval: int) -> dict:
        return self.session.get_klines(
            symbol=self.symbol, 
            interval=interval, 
            limit=limit
        )


    async def trades(self, limit: int) -> dict:
        return self.session.get_recent_trades(
            symbol=self.symbol, 
            limit=limit
        )


from pybit.unified_trading import HTTP


class BybitPublicGet:


    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self._session = None
        self.category = "linear"


    @property
    def session(self):
        if self._session is None:
            self._session = HTTP()
                
        return self._session


    async def klines(self, interval: int, limit: int) -> list:
        return self.session.get_kline(
            category=self.category, 
            symbol=self.symbol, 
            interval=str(interval),
            limit=str(limit)
        )


    async def trades(self, limit: int) -> list:
        return self.session.get_public_trade_history(
            category=self.category, 
            symbol=self.symbol, 
            limit=str(limit)
        )
        
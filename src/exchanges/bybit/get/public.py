
from pybit.unified_trading import HTTP
from src.sharedstate import SharedState


class BybitPublicClient:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self._session = None

        self.symbol = self.ss.bybit_symbol
        self.category = "linear"


    @property
    def session(self):
        if self._session is None:
            self._session = HTTP(
                api_key=self.ss.api_key, 
                api_secret=self.ss.api_secret
            )
                

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
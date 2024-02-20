from pybit.unified_trading import HTTP
from typing import List
from src.sharedstate import SharedState


class BybitPublicClient:
    category = "linear"

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.key, self.secret = self.ss.api_key, self.ss.api_secret
        self.session = HTTP(api_key=self.key, api_secret=self.secret)
        self.symbol: str = self.ss.bybit_symbol

    async def klines(self, interval: int, limit: int) -> List:
        return self.session.get_kline(
            category=self.category, 
            symbol=self.symbol, 
            interval=str(interval),
            limit=str(limit)
        )

    async def trades(self, limit: int) -> List:
        return self.session.get_public_trade_history(
            category=self.category, 
            symbol=self.symbol, 
            limit=str(limit)
        )
    
    async def instrument_info(self) -> List:
        return self.session.get_instruments_info(
            category=self.category,
            symbol=self.symbol
        )
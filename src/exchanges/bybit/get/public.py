
from pybit.unified_trading import HTTP
from src.sharedstate import SharedState


class BybitPublicClient:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.symbol = self.ss.bybit_symbol

        self.session = HTTP(
            api_key=self.ss.api_key, 
            api_secret=self.ss.api_secret
        )
             

    async def klines(self, interval: int):

        data = self.session.get_kline(
            category='linear', 
            symbol=self.symbol,
            interval=str(interval)
        )

        return data


    async def trades(self, limit: int):

        data = self.session.get_public_trade_history(
            category='linear', 
            symbol=self.symbol,
            limit=str(limit)
        )

        return data
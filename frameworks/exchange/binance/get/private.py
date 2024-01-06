
from typing import List

from binance import AsyncClient
from frameworks.sharedstate.private import PrivateDataSharedState


class BinancePrivateGet:

    
    def __init__(
        self, 
        sharedstate: PrivateDataSharedState, 
        symbol: str
    ) -> None:

        self.binance = sharedstate.binance["API"]
        self.symbol = symbol

        self.session = AsyncClient(
            api_key=self.binance["key"],
            api_secret=self.binance["secret"],
        )


    async def open_orders(self) -> List:
        return self.session.futures_get_open_orders(
            symbol=self.symbol
        )


    async def current_position(self) -> List:
        return self.session.futures_position_information(
            symbol=self.symbol
        )
        

    async def exchange_info(self) -> List:
        return self.session.get_exchange_info()


    async def account_info(self) -> List:
        return self.session.get_account()
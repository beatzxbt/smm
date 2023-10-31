
from pybit.unified_trading import HTTP
from frameworks.sharedstate.private import PrivateDataSharedState


class BybitPrivateGet:


    def __init__(self, sharedstate: PrivateDataSharedState, symbol: str) -> None:
        self.bybit = sharedstate.bybit
        self.symbol = symbol
        self._session = None
        self.category = "linear"


    @property
    def session(self):
        if self._session is None:
            self._session = HTTP(
                api_key=self.bybit["API"]["key"],
                api_secret=self.bybit["API"]["secret"],
            )
                
        return self._session


    async def open_orders(self) -> list:
        return self.session.get_open_orders(
            category=self.category, 
            symbol=self.symbol, 
            limit=str(50)
        )


    async def current_position(self) -> list:
        return self.session.get_positions(
            category=self.category, 
            symbol=self.symbol
        )
        
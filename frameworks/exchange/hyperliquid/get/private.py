
from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.api import API
from frameworks.sharedstate.private import PrivateDataSharedState


class HyperLiquidPrivateGet:


    def __init__(self, sharedstate: PrivateDataSharedState, symbol: str) -> None:
        self.hlq = sharedstate.hyperliquid
        self.symbol = symbol
        self._session = None


    @property
    def session(self):
        if self._session is None:
            exchange = Exchange(self.hlq["API"]["secret"])
                
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
        

    async def wallet_info(self) -> list:
        return self.session.get_wallet_balance(
            accountType="UNIFIED"
        )
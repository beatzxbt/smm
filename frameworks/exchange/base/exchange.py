from abc import ABC, abstractmethod
from typing import Dict, Optional, Union

from frameworks.tools.logging import Logger
from frameworks.exchange.base.client import Client


class Exchange(ABC):
    """
    Base exchange class

    Contains only essential functions which likely all strategies
    will use. If additional functions are required (for basic exchange 
    information initialization like tick/lot sizes), these should be 
    added to the inherited class.
    """
    def __init__(self, client: Client) -> None:
        self.client = client

    def load_required_refs(self, logging: Logger, symbol: str, data: Dict) -> None:
        self.logging = logging
        self.symbol = symbol
        self.data = data
        self.client.load_required_refs(logging=logging)

    @abstractmethod
    async def warmup(self) -> None:
        pass
    
    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: int,
        orderType: int,
        size: float,
        price: Optional[float]=None,
        orderId: Optional[Union[str, int]]=None
    ) -> Dict:
        pass
    
    @abstractmethod
    async def amend_order(
        self,
        symbol: str,
        orderId: Union[str, int],
        side: int,
        size: float,
        price: float,
    ) -> Dict:
        pass

    @abstractmethod
    async def cancel_order(
        self, 
        symbol: str,
        orderId: Union[str, int]
    ) -> Dict:
        pass

    @abstractmethod
    async def cancel_all_orders(
        self, 
        symbol: str
    ) -> Dict:
        pass

    @abstractmethod
    async def get_ohlcv(
        self, 
        symbol: str, 
        interval: int
    ) -> Dict:
        pass

    @abstractmethod
    async def get_trades(
        self, 
        symbol: str, 
    ) -> Dict:
        pass

    @abstractmethod
    async def get_orderbook(
        self, 
        symbol: str, 
    ) -> Dict:
        pass

    @abstractmethod
    async def get_ticker(
        self, 
        symbol: str, 
    ) -> Dict:
        pass

    @abstractmethod
    async def get_open_orders(
        self, 
        symbol: str
    ) -> Dict:
        pass

    @abstractmethod
    async def get_position(
        self, 
        symbol: str
    ) -> Dict:
        pass
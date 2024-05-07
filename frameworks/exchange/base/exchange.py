from abc import ABC, abstractmethod
from typing import Dict, Optional, Union
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

    async def submit(self, method: str, endpoint: str, payload: Dict) -> Union[Dict, None]:
        """Submit a request to the client"""
        await self.client.send(method, endpoint, payload)

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: str,
        orderType: str,
        size: float,
        price: Optional[float]=None,
        orderId: Optional[str]=None
    ) -> Union[Dict, str]:
        pass
    
    @abstractmethod
    async def amend_order(
        self,
        symbol: str,
        orderId: str,
        size: float,
        price: float,
    ) -> Union[Dict, None]:
        pass

    @abstractmethod
    async def cancel_order(
        self, 
        orderId: str
    ) -> Union[Dict, None]:
        pass

    @abstractmethod
    async def cancel_all_orders(
        self, 
        symbol: str
    ) -> Union[Dict, None]:
        pass

    @abstractmethod
    async def get_ohlcv(
        self, 
        symbol: str, 
        interval: int
    ) -> Union[Dict, None]:
        pass

    @abstractmethod
    async def get_trades(
        self, 
        symbol: str, 
    ) -> Union[Dict, None]:
        pass

    @abstractmethod
    async def get_orderbook(
        self, 
        symbol: str, 
    ) -> Union[Dict, None]:
        pass

    @abstractmethod
    async def get_open_orders(
        self, 
        symbol: str
    ) -> Union[Dict, None]:
        pass

    @abstractmethod
    async def get_open_position(
        self, 
        symbol: str
    ) -> Union[Dict, None]:
        pass
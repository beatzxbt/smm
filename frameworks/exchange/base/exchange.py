from abc import ABC, abstractmethod
from typing import Dict, Optional, Union

from frameworks.tools.logging import Logger
from frameworks.exchange.base.client import Client


class Exchange(ABC):
    def __init__(self, client: Client) -> None:
        """
        Initializes the Exchange class with a client.

        Parameters
        ----------
        client : Client
            The client instance to interact with the exchange.
        """
        self.client = client

    def load_required_refs(self, logging: Logger, symbol: str, data: Dict) -> None:
        """
        Loads required references such as logging, symbol, and data.

        Parameters
        ----------
        logging : Logger
            The Logger instance for logging events and messages.

        symbol : str
            The trading symbol.

        data : Dict
            A Dictionary holding various shared state data.

        """
        self.logging = logging
        self.symbol = symbol
        self.data = data
        self.client.load_required_refs(logging=logging)

    @abstractmethod
    async def warmup(self) -> None:
        """
        Abstract method for warming up the exchange-specific data.
        """
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
        """
        Abstract method to create an order.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        side : int
            The side of the order.

        orderType : int
            The type of the order.

        size : float
            The size of the order.

        price : float, optional
            The price of the order (for limit orders).

        orderId : str or int, optional
            The ID of the order.

            
        Returns
        -------
        Dict
            The response from the exchange.
        """
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
        """
        Abstract method to amend an existing order.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        orderId : str or int
            The ID of the order to be amended.

        side : int
            The side of the order.

        size : float
            The new size of the order.

        price : float
            The new price of the order.


        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    async def cancel_order(
        self, 
        symbol: str,
        orderId: Union[str, int]
    ) -> Dict:
        """
        Abstract method to cancel an existing order.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        orderId : str or int
            The ID of the order to be canceled.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    async def cancel_all_orders(
        self, 
        symbol: str
    ) -> Dict:
        """
        Abstract method to cancel all existing orders for a symbol.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    async def get_ohlcv(
        self, 
        symbol: str, 
        interval: Union[int, str]
    ) -> Dict:
        """
        Abstract method to get OHLCV (Open, High, Low, Close, Volume) data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        interval : Union[int, str]
            The interval for the OHLCV data.

        Returns
        -------
        Dict
            The OHLCV data from the exchange.
        """
        pass

    @abstractmethod
    async def get_trades(
        self, 
        symbol: str
    ) -> Dict:
        """
        Abstract method to get recent trades.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The trades data from the exchange.
        """
        pass

    @abstractmethod
    async def get_orderbook(
        self, 
        symbol: str
    ) -> Dict:
        """
        Abstract method to get an orderbook snapshot.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The order book data from the exchange.
        """
        pass

    @abstractmethod
    async def get_ticker(
        self, 
        symbol: str
    ) -> Dict:
        """
        Abstract method to get ticker data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The ticker data from the exchange.
        """
        pass

    @abstractmethod
    async def get_open_orders(
        self, 
        symbol: str
    ) -> Dict:
        """
        Abstract method to get open orders.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The open orders data from the exchange.
        """
        pass

    @abstractmethod
    async def get_position(
        self, 
        symbol: str
    ) -> Dict:
        """
        Abstract method to get current position data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Dict
            The position data from the exchange.
        """
        pass

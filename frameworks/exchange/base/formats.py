from abc import ABC, abstractmethod
from typing import Dict, Union, Optional

from frameworks.exchange.base.types import StrNumConverter


class Formats(ABC):
    def __init__(
        self, convert_side: StrNumConverter, convert_order_type: StrNumConverter
    ) -> None:
        self.convert_side = convert_side
        self.convert_order_type = convert_order_type

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: Union[int, float],
        orderType: Union[int, float],
        size: float,
        price: Optional[float] = None,
        orderId: Optional[Union[str, int]] = None,
    ) -> Dict:
        """
        Abstract method to create an order.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        side : Union[int, float]
            The side of the order.

        orderType : Union[int, float]
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
        side: Union[int, float],
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

        side : Union[int, float]
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
    async def cancel_order(self, symbol: str, orderId: Union[str, int]) -> Dict:
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
    async def cancel_all_orders(self, symbol: str) -> Dict:
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
        self, symbol: str, interval: Union[int, str]
    ) -> Union[Dict, str]:
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
        Union[Dict, str]
            The OHLCV data from the exchange.
        """
        pass

    @abstractmethod
    async def get_trades(self, symbol: str) -> Union[Dict, str]:
        """
        Abstract method to get recent trades.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Union[Dict, str]
            The trades data from the exchange.
        """
        pass

    @abstractmethod
    async def get_orderbook(self, symbol: str) -> Union[Dict, str]:
        """
        Abstract method to get an orderbook snapshot.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Union[Dict, str]
            The order book data from the exchange.
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Union[Dict, str]:
        """
        Abstract method to get ticker data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Union[Dict, str]
            The ticker data from the exchange.
        """
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: str) -> Union[Dict, str]:
        """
        Abstract method to get open orders.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Union[Dict, str]
            The open orders data from the exchange.
        """
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Union[Dict, str]:
        """
        Abstract method to get current position data.

        Parameters
        ----------
        symbol : str
            The trading symbol.

        Returns
        -------
        Union[Dict, str]
            The position data from the exchange.
        """
        pass

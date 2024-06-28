from abc import ABC, abstractmethod
from typing import Dict, Union

from frameworks.exchange.base.types import (
    Order,
    SideConverter,
    OrderTypeConverter,
    TimeInForceConverter,
    PositionDirectionConverter,
)

class Formats(ABC):
    recvWindow = 1000

    def __init__(
        self,
        convert_side: SideConverter,
        convert_order_type: OrderTypeConverter,
        convert_time_in_force: TimeInForceConverter,
        convert_position_direction: PositionDirectionConverter 
    ) -> None:
        self.convert_side = convert_side
        self.convert_order_type = convert_order_type
        self.convert_tif = convert_time_in_force
        self.convert_pos_direction = convert_position_direction

    @abstractmethod
    def create_order(
        self,
        order: Order
    ) -> Dict:
        """
        Abstract method to create an order.

        Parameters
        ----------
        order: Order
            The order to be sent to the exchange. 

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    def amend_order(
        self,
        order: Order
    ) -> Dict:
        """
        Abstract method to amend an existing order.

        Parameters
        ----------
        order: Order
            The order to be sent to the exchange. 

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    def cancel_order(
        self,
        order: Order
    ) -> Dict:
        """
        Abstract method to cancel an existing order.

        Parameters
        ----------
        order: Order
            The order to amend. 

        Returns
        -------
        Dict
            The response from the exchange.
        """
        pass

    @abstractmethod
    def cancel_all_orders(self, symbol: str) -> Dict:
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
    def get_ohlcv(self, symbol: str, interval: Union[int, str]) -> Union[Dict, str]:
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
    def get_trades(self, symbol: str) -> Union[Dict, str]:
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
    def get_orderbook(self, symbol: str) -> Union[Dict, str]:
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
    def get_ticker(self, symbol: str) -> Union[Dict, str]:
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
    def get_open_orders(self, symbol: str) -> Union[Dict, str]:
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
    def get_position(self, symbol: str) -> Union[Dict, str]:
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

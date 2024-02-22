from binance.client import Client
from typing import Dict
from src.sharedstate import SharedState

class BinancePublicGet:
    """
    Provides access to public data from Binance such as order books, klines (candlesticks),
    and recent trades for a specified symbol.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState containing configuration and shared data.
    symbol : str
        The trading symbol to query data for.
    client : Client
        The Binance client from the python-binance package for making API requests.

    Methods
    -------
    orderbook(limit: int) -> Dict:
        Fetches the order book for the symbol up to a specified limit.
    klines(limit: int, interval: int) -> Dict:
        Retrieves klines (candlestick data) for the symbol, given a limit and time interval.
    trades(limit: int) -> Dict:
        Obtains recent trades for the symbol up to a specified limit.
    instrument_info() -> Dict:
        Gets detailed symbol information.
    """

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BinancePublicGet class with shared state and prepares the Binance client.

        Parameters
        ----------
        ss : SharedState
            The shared state instance from which the Binance symbol is retrieved.
        """
        self.ss = ss
        self.symbol: str = self.ss.binance_symbol
        self.client = Client()

    async def orderbook(self, limit: int) -> Dict:
        """
        Fetches the current order book for the specified symbol.

        Parameters
        ----------
        limit : int
            The maximum number of orders to retrieve for both the buy and sell sides.

        Returns
        -------
        Dict
            A dictionary containing the current order book, including bids and asks.
        """
        return self.client.get_order_book(symbol=self.symbol, limit=limit)

    async def klines(self, limit: int, interval: str) -> Dict:
        """
        Retrieves klines (candlestick data) for the specified symbol.

        Parameters
        ----------
        limit : int
            The maximum number of klines to retrieve.
        interval : str
            The interval between each kline (e.g., '1m', '1h', '1d').

        Returns
        -------
        Dict
            A dictionary containing the kline data.
        """
        return self.client.get_klines(symbol=self.symbol, interval=interval, limit=limit)

    async def trades(self, limit: int) -> Dict:
        """
        Obtains a list of recent trades for the specified symbol.

        Parameters
        ----------
        limit : int
            The maximum number of trades to retrieve.

        Returns
        -------
        Dict
            A dictionary containing recent trade data.
        """
        return self.client.get_recent_trades(symbol=self.symbol, limit=limit)
    
    async def instrument_info(self) -> Dict:
        """
        Gets detailed information about the specified symbol.

        Returns
        -------
        Dict
            A dictionary containing detailed symbol information, such as trading pairs and limits.
        """
        return self.client.get_symbol_info(symbol=self.symbol)

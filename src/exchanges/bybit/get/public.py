from pybit.unified_trading import HTTP
from typing import List
from src.sharedstate import SharedState

class BybitPublicClient:
    """
    A client for fetching public trading data from Bybit, such as kline (candlestick) data, 
    recent trades, and instrument information.

    Attributes
    ----------
    category : str
        The category of the trading instrument, e.g., "linear".
    ss : SharedState
        An instance of SharedState containing shared application data.
    key : str
        The API key obtained from the shared state for authorized requests.
    secret : str
        The API secret obtained from the shared state for signing requests.
    session : HTTP
        An instance of the HTTP client from pybit for making API requests.
    symbol : str
        The trading symbol to query data for, obtained from the shared state.

    Methods
    -------
    klines(interval: int, limit: int) -> List:
        Fetches kline data for the specified interval and limit.
    trades(limit: int) -> List:
        Retrieves the recent trades up to the specified limit.
    instrument_info() -> List:
        Gets the instrument information for the specified symbol.
    """

    category = "linear"

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BybitPublicClient with shared state, API credentials, and trading symbol.

        Parameters
        ----------
        ss : SharedState
            An instance of SharedState containing shared application data.
        """
        self.ss = ss
        self.key, self.secret = self.ss.api_key, self.ss.api_secret
        self.session = HTTP(api_key=self.key, api_secret=self.secret)
        self.symbol = self.ss.bybit_symbol

    async def klines(self, interval: int, limit: int) -> List:
        """
        Asynchronously fetches kline data for the specified trading symbol, interval, and limit.

        Parameters
        ----------
        interval : int
            The time interval for the klines.
        limit : int
            The maximum number of kline entries to retrieve.

        Returns
        -------
        List
            A list of kline data entries.
        """
        return self.session.get_kline(
            category=self.category, 
            symbol=self.symbol, 
            interval=str(interval),
            limit=str(limit)
        )

    async def trades(self, limit: int) -> List:
        """
        Asynchronously retrieves recent trade history for the specified trading symbol and limit.

        Parameters
        ----------
        limit : int
            The maximum number of trade entries to retrieve.

        Returns
        -------
        List
            A list of recent trade data entries.
        """
        return self.session.get_public_trade_history(
            category=self.category, 
            symbol=self.symbol, 
            limit=str(limit)
        )
    
    async def instrument_info(self) -> List:
        """
        Asynchronously fetches instrument information for the specified trading symbol.

        Returns
        -------
        List
            A list containing instrument information.
        """
        return self.session.get_instruments_info(
            category=self.category,
            symbol=self.symbol
        )
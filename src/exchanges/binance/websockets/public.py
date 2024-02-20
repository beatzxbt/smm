from typing import List, Tuple
from src.exchanges.binance.endpoints import WsStreamLinks
from src.sharedstate import SharedState

class BinancePublicWs:
    """
    Handles the creation of WebSocket requests for Binance public streams.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState containing shared application data.
    symbol : str
        The trading symbol in lowercase, extracted from SharedState.
    spot_base_url : str
        The base URL for the Binance spot public WebSocket stream.

    Methods
    -------
    multi_stream_request(topics: List[str], **kwargs) -> Tuple[str, List[str]]:
        Constructs a WebSocket URL and a list of stream topics based on the provided arguments.
    """

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BinancePublicWs instance with shared state and pre-configures necessary attributes.

        Parameters
        ----------
        ss : SharedState
            Shared application state containing configuration and runtime information.
        """
        self.ss = ss
        self.symbol: str = self.ss.binance_symbol.lower()
        self.futures_base_url = WsStreamLinks.FUTURES_PUBLIC_STREAM

    def multi_stream_request(self, topics: List[str], **kwargs) -> Tuple[str, List[str]]:
        """
        Constructs and returns a WebSocket request URL and a corresponding list of topics for subscription.

        Parameters
        ----------
        topics : List[str]
            A list of topics to subscribe to. Supported topics include "Trades", "Orderbook", "BBA", and "Kline".
        **kwargs : dict
            Additional keyword arguments for specific subscriptions, such as the interval for "Kline" topics.

        Returns
        -------
        Tuple[str, List[str]]
            A tuple containing the WebSocket URL (str) and a list of stream topics (List[str]).

        Notes
        -----
        - The "Kline" topic requires an "interval" keyword argument.
        - The URL and topics are constructed based on the Binance WebSocket API documentation.
        """

        list_of_topics = []
        url = self.futures_base_url + "/stream?streams="

        for topic in topics:
            stream = ""
            if topic == "Trades":
                stream = f"{self.symbol}@trade/"
            elif topic == "Orderbook":
                stream = f"{self.symbol}@depth@100ms/"
            elif topic == "BBA":
                stream = f"{self.symbol}@bookTicker/"
            elif topic == "Kline" and "interval" in kwargs:
                stream = f"{self.symbol}@kline_{kwargs['interval']}/"

            if stream:
                url += stream
                list_of_topics.append(stream[:-1])

        return url[:-1], list_of_topics
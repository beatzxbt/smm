import json
from src.sharedstate import SharedState

class BybitPublicWs:
    """
    Manages the WebSocket connection for Bybit's public streams, handling subscription requests for various topics.

    Attributes
    ----------
    ss : SharedState
        An instance of SharedState for managing shared application data.
    symbol : str
        The trading symbol in uppercase, extracted from SharedState.

    Methods
    -------
    multi_stream_request(topics: list, **kwargs) -> tuple:
        Generates a WebSocket subscription request for a list of topics.
    """

    def __init__(self, ss: SharedState) -> None:
        """
        Initializes the BybitPublicWs with a reference to SharedState and sets the trading symbol.

        Parameters
        ----------
        ss : SharedState
            The shared state instance for managing application data.
        """
        self.ss = ss
        self.symbol = self.ss.bybit_symbol.upper()

    def multi_stream_request(self, topics: list, **kwargs) -> tuple:
        """
        Constructs and returns a WebSocket request for subscribing to specified public topics and a list of these topics.

        Supported topics include Liquidation, Trades, Ticker, Orderbook, BBA, and Kline, with optional depth for Orderbook
        and interval for Kline provided via keyword arguments.

        Parameters
        ----------
        topics : list
            A list of topics to subscribe to.
        **kwargs : dict
            Additional keyword arguments for specific topics, such as 'depth' for Orderbook and 'interval' for Kline.

        Returns
        -------
        tuple
            A tuple containing the subscription request as a JSON string and a list of topics.

        Notes
        -----
        - The 'depth' keyword argument specifies the depth of the Orderbook.
        - The 'interval' keyword argument specifies the interval for Kline data.
        """
        list_of_topics = []

        for topic in topics:
            if topic == "Liquidation":
                list_of_topics.append(f"liquidation.{self.symbol}")
            elif topic == "Trades":
                list_of_topics.append(f"publicTrade.{self.symbol}")
            elif topic == "Ticker":
                list_of_topics.append(f"tickers.{self.symbol}")
            elif topic == "BBA":
                list_of_topics.append(f"orderbook.1.{self.symbol}")
            elif topic == "Orderbook" and "depth" in kwargs:
                list_of_topics.append(f"orderbook.{kwargs['depth']}.{self.symbol}")
            elif topic == "Kline" and "interval" in kwargs:
                list_of_topics.append(f"kline.{kwargs['interval']}.{self.symbol}")

        req = json.dumps({"op": "subscribe", "args": list_of_topics})

        return req, list_of_topics
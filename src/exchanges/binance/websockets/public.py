
from src.exchanges.binance.endpoints import WsStreamLinks
from src.sharedstate import SharedState


class BinancePublicWs:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.symbol = self.ss.binance_symbol.lower()

        self.spot_base = WsStreamLinks.SPOT_PUBLIC_STREAM
        self.futures_base = WsStreamLinks.FUTURES_PUBLIC_STREAM


    def multi_stream_request(self, topics: list, **kwargs) -> tuple:
        """
        Creates a tuple of (str, list) \n
        Containing the websocket url [0] and list of streams [1]

        _______________________________________________________________

        Current supported topics are: \n
        -> Trades \n
        -> BBA \n
        -> Orderbook (Returns all levels in orderbook by default) \n
        -> Kline (Requires {interval: int} kwarg)
        """

        topiclist = []

        url = self.spot_base + "/stream?streams="

        for topic in topics:
            if topic == "Trades":
                stream = "{}@trade/".format(self.symbol)

            if topic == "Orderbook":
                stream = "{}@depth@100ms/".format(self.symbol)

            if topic == "BBA":
                stream = "{}@bookTicker/".format(self.symbol)

            if topic == "Kline" and kwargs["interval"] is not None:
                stream = "{}@kline_{}/".format(self.symbol, kwargs["interval"])

            url += stream
            topiclist.append(stream[:-1])

        return url[:-1], topiclist
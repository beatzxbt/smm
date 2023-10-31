
from frameworks.exchange.binance.endpoints import WsStreamLinks


class BinancePublicWs:


    def __init__(self) -> None:
        self.spot_base = WsStreamLinks.SPOT_PUBLIC_STREAM
        self.futures_base = WsStreamLinks.FUTURES_PUBLIC_STREAM


    def multi_stream_request(self, symbol: str, topics: list, **kwargs) -> tuple:
        """
        Creates a tuple of (str, list) \n
        Containing the websocket url [0] and list of streams [1]

        _______________________________________________________________

        Current supported topics are: \n
        -> Trades \n
        -> BBA \n
        -> Orderbook (returns all levels in orderbook by default) \n
        -> Kline (requires {interval: int} kwarg)
        """

        topiclist = []

        url = self.spot_base + "/stream?streams="

        for topic in topics:
            if topic == "Trades":
                stream = "{}@trade/".format(symbol)

            if topic == "Orderbook":
                stream = "{}@depth@100ms/".format(symbol)

            if topic == "BBA":
                stream = "{}@bookTicker/".format(symbol)

            if topic == "Kline" and kwargs["interval"] is not None:
                stream = "{}@kline_{}/".format(symbol, kwargs["interval"])

            url += stream
            topiclist.append(stream[:-1])

        return url[:-1], topiclist
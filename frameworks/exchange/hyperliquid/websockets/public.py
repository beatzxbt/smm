
import json


class HyperLiquidPublicWsInit:


    def __init__(self, symbol: str):
        self.symbol = symbol


    def multi_stream_request(self, topics: list, **kwargs) -> tuple:
        """
        Creates a tuple of (JSON, list) \n
        Containing the websocket request [0] and list of streams [1]

        _______________________________________________________________

        Current supported topics are: \n
        -> Trades \n
        -> Ticker \n
        -> Orderbook \n
        -> BBA (fastest stream for L1) \n
        -> Kline (requires {interval: int} kwarg)
        """

        topiclist = []

        for topic in topics:

            if topic == "Liquidation":
                topiclist.append({"type": ___, })

            if topic == "Trades":
                topiclist.append({"type": ___, })

            if topic == "BBA":
                topiclist.append({"type": ___, })
            
            if topic == "Orderbook":
                topiclist.append({"type": "l2Book", "coin": self.symbol})

            if topic == "Kline" and kwargs["interval"] is not None:
                topiclist.append({"type": "candle", "coin": self.symbol, "interval": kwargs["interval"]})

        req = json.dumps({"method": "subscribe", "subscription": topiclist})

        return req, topiclist

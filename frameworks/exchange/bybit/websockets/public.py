
import json


class BybitPublicWsInit:


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

            # if topic == "Liquidation":
            #     topiclist.append("liquidation.{}".format(self.symbol))

            if topic == "Trades":
                topiclist.append("publicTrade.{}".format(self.symbol))

            if topic == "Ticker":
                topiclist.append("tickers.{}".format(self.symbol))

            if topic == "BBA":
                topiclist.append("orderbook.{}.{}".format(1, self.symbol))
            
            if topic == "Orderbook":
                topiclist.append("orderbook.{}.{}".format(500, self.symbol))

            if topic == "Kline" and kwargs["interval"] is not None:
                topiclist.append("kline.{}.{}".format(kwargs["interval"], self.symbol))

        req = json.dumps({"op": "subscribe", "args": topiclist})

        return req, topiclist

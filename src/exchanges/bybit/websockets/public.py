
import json
from src.sharedstate import SharedState


class BybitPublicWs:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.symbol = self.ss.bybit_symbol.upper()


    def multi_stream_request(self, topics: list, **kwargs) -> tuple:
        """
        Creates a tuple of (JSON, list) \n
        Containing the websocket request [0] and list of streams [1]

        _______________________________________________________________

        Current supported topics are: \n
        -> Liquidation \n
        -> Trades \n
        -> Ticker \n
        -> Orderbook (Requires {depth: int} kwarg) \n
        -> BBA (fastest stream for L1) \n
        -> Kline (Requires {interval: int} kwarg)
        """

        topiclist = []

        for topic in topics:

            if topic == "Liquidation":
                topiclist.append("liquidation.{}".format(self.symbol))

            if topic == "Trades":
                topiclist.append("publicTrade.{}".format(self.symbol))

            if topic == "Ticker":
                topiclist.append("tickers.{}".format(self.symbol))

            if topic == "BBA":
                topiclist.append("orderbook.{}.{}".format(1, self.symbol))
            
            if topic == "Orderbook" and kwargs["depth"] is not None:
                topiclist.append("orderbook.{}.{}".format(kwargs["depth"], self.symbol))

            if topic == "Kline" and kwargs["interval"] is not None:
                topiclist.append("kline.{}.{}".format(kwargs["interval"], self.symbol))

        req = json.dumps({"op": "subscribe", "args": topiclist})

        return req, topiclist

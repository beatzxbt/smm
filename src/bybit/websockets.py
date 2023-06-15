import json
import time
import hmac
import hashlib


class PrivateWs:


    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.expires = str(int((time.time() + 5) * 1000))
     

    def auth(self) -> json:
        """
        Generates an authentication JSON for a private WS connection
        """
    
        signature = hmac.new(bytes(self.api_secret, "utf-8"), bytes(f"GET/realtime{self.expires}", "utf-8"), hashlib.sha256)
        req = json.dumps({"op": "auth", "args": [self.api_key, self.expires, str(signature.hexdigest())]})

        return req
    

    def multi_stream_request(self, topics: list) -> tuple:
        """
        Creates a tuple of (JSON, list) \n
        Containing the websocket request [0] and list of streams [1]

        _______________________________________________________________
        
        Current supported topics are: \n
        -> Position \n
        -> Execution \n
        -> Order
        """

        topiclist = []

        for topic in topics:

            if topic == 'Position':
                topiclist.append('position')

            if topic == 'Execution':
                topiclist.append('execution')

            if topic == 'Order':
                topiclist.append('order')

        req = json.dumps({"op": 'subscribe', "args": topiclist})

        return req, topiclist



class PublicWs:


    def __init__(self, symbol: str) -> None:
        self.symbol = symbol.upper()
    

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
        -> Kline (Requires {interval: int} kwarg)
        """

        topiclist = []

        for topic in topics:

            if topic == 'Liquidation':
                topiclist.append('liquidation.{}'.format(self.symbol))

            if topic == 'Trades':
                topiclist.append('publicTrade.{}'.format(self.symbol))

            if topic == 'Ticker':
                topiclist.append('tickers.{}'.format(self.symbol))

            if topic == 'Orderbook' and kwargs['depth'] is not None:
                topiclist.append('orderbook.{}.{}'.format(kwargs['depth'], self.symbol))

            if topic == 'Kline' and kwargs['interval'] is not None: 
                topiclist.append('kline.{}.{}'.format(kwargs['interval'], self.symbol))

        req = json.dumps({"op": 'subscribe', "args": topiclist})

        return req, topiclist




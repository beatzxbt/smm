from src.binance.websockets.endpoints import WsStreamLinks


class PublicWs:


    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate
        self.symbol = str(self.ss.binance_symbol).lower()
        
        self.spot_base = WsStreamLinks.spot_public_stream()
        self.futures_base = WsStreamLinks.futures_public_stream()
    

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

            if topic == 'Trades':
                stream = '{}@trade/'.format(self.symbol)

            if topic == 'Orderbook':
                stream = '{}@depth@100ms/'.format(self.symbol)

            if topic == 'BBA':
                stream = '{}@bookTicker/'.format(self.symbol)

            if topic == 'Kline' and kwargs['interval'] is not None: 
                stream = '{}@kline_{}/'.format(self.symbol, kwargs['interval'])

            url += stream
            topiclist.append(stream[:-1])

        return url[:-1], topiclist



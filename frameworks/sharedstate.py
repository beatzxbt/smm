import numpy as np
from numpy_ringbuffer import RingBuffer
from collections import deque
from frameworks.tools.logger import Logger
from frameworks.tools.orderbook import Orderbook
from frameworks.exchange.brrr.brrrclient import BrrrClient
from frameworks.exchange.ccxt.exchange import CcxtClient
from typing import Tuple, List, Dict, Coroutine, Union, NoReturn

custom_clients = [
    "binance", 
    "bybit", 
    "hyperliquid",
    # "okx",
    # "kucoin"
]

class SharedState:
    """
    A class for managing shared state across various components of a trading system. 
    It handles the initialization and management of clients, market data, private account data, 
    and more for different exchanges and trading pairs.

    Attributes
    ----------
    logging : Logger
        Logger instance for logging messages.

    market : Dict
        A dictionary to store market data keyed by exchange and symbol.

    private : Dict
        A dictionary to store private account data keyed by exchange.

    clients : Dict
        A dictionary to store instances of exchange clients keyed by exchange name.

    primary_pair : str
        The name of the primary exchange for quoting.
    """

    def __init__(self) -> None:
        """
        Initialize the sharedstate class, to feed into all other classes

        Arguements:
            pairs: A list consisting of each tuple(exchange, symbol) pair

        Return:
            None
        """
        self.logging = Logger

        self.market = {}
        self.private = {}
        self.clients = {}
        self.primary_pair = None

    async def load_markets(self, primary_pair: Tuple[str, str], pairs: List[Tuple[str, str]]) -> None:
        """
        Initializes the necessary clients, market data, and private data for 
        specified exchange-symbol pairs and sets up the primary exchange.

        More documentation found in self._initialize_().

        Parameters
        ----------
        primary_pair : Tuple[str, str]
            The exchange and symbol pair intended for primary quoting.

        pairs : List[Tuples]
            A list of tuples containing exchange and symbol pairs.
        """
        unique_exchanges = set()

        for pair in pairs:
            pair = self._pair_to_lower_(pair)
            primary = pair[0] == primary_pair[0]
            unique_exchanges.add((pair[0], primary))
            self._create_market_pair_(pair)
            self._create_private_pair_(pair, primary)
        
        for exchange, primary in unique_exchanges:
            self._create_client_pair_(exchange, primary)
        
    def _create_market_pair_(self, pair: Tuple[str, str]) -> Dict:
        """
        Creates market data structures for a given exchange-symbol pair.

        Parameters
        ----------
        pair : Tuple[str, str]
            The exchange-symbol pair for which to create market data.

        Returns
        -------
        Dict
            The initialized market data structure for the given pair.
        """
        exchange, symbol = pair

        if exchange not in self.market:
            self.market[exchange] = {}
        
        self.market[exchange][symbol] = {
            "bba": np.ones((2, 2), dtype=float),
            "book": Orderbook(500),
            "trades": RingBuffer(10000, dtype=(float, 4)),
            "ohlcv": RingBuffer(1000, dtype=(float, 6)),
            # "liquidations": RingBuffer(1000, dtype=(float, 4))

            "lastPrice": None,
            "markPrice": None,
            "indexPrice": None,
            "fundingRate": None,
            "fundingTimestamp": None,
            "24hVol": None,
            "tickSize": None,
            "lotSize": None
        }

    def _create_private_pair_(self, pair: Tuple[str, str], primary: bool=False) -> Union[Dict, None]:
        """
        Creates private account data structures for a given exchange-symbol pair.

        Parameters
        ----------
        pair : Tuple[str, str]
            The exchange-symbol pair for which to create private account data.

        primary : bool, optional
            Flag to indicate if the pair is for the primary exchange.

        Returns
        -------
        Dict or None
            The initialized private account data for the given pair or None if not primary.
        """
        if not primary:
            return None
        
        exchange, symbol = pair

        if exchange not in self.private:
            self.private[exchange] = {
                "API": {
                    "key": "",
                    "secret": "",
                    "rateLimits": {}, # TODO: Populated by client
                    "latency": RingBuffer(100, dtype=float), # TODO: Populated by client
                    "takerFees": None,
                    "makerFees": None,
                },
                "currentBalance": None
            }
        
        self.private[exchange][symbol] = {
            "openOrders": {},
            "executions": deque(1000),
            "currentPosition": {}
        }

    def _create_client_pair_(self, pair: Tuple[str, str], primary: bool=False) -> Dict:
        """
        Initializes and stores a client for a given exchange.

        Parameters
        ----------
        pair : Tuple[str, str]
            The exchange-symbol pair for which to create the client.

        primary : bool, optional
            Flag to indicate if the pair is for the primary exchange.

        Returns
        -------
        Dict or None
            The initialized client for the given exchange or None if already initialized.
        """
        exchange = pair[0]

        if exchange in self.clients:
            return None

        try:
            if exchange in custom_clients:
                self.clients[exchange] = BrrrClient(exchange, self.market, self.private, primary)
            else:
                self.clients[exchange] = CcxtClient(exchange, self.market, self.private, primary)

        except Exception as e:
            self.logging.critical(f"Error initializing {exchange}: {e}")
            raise e
    
    async def _initialize_(self, pair: Tuple[str, str], primary: bool=False) -> None:
        """
        Run initialization tasks on each pair, doing:  
        -> Acquire user's maker/taker fees information
        -> Acquire user's rate limits
        -> Establishing the TCP connection to server (ping) 
        -> Acquire symbol's tick/lot sizes
        -> Fill all relevant market data points (trades/ob/ohlcv/ticker)
        -> Start relevant websocket feeds

        If the pair is not a primary exchange, then only the final 
        two tasks are ran

        Parameters
        ----------
        pair : Tuple[str, str]
            The exchange-symbol pair to initialize.

        primary : bool, optional
            Flag to indicate if the pair is for the primary exchange.
        """
        await self.clients[pair[0]].initialize(primary)
    
    @staticmethod
    def _pair_to_lower_(pair: Tuple[str, str]) -> Tuple[str, str]:
        return tuple(i.lower() for i in pair)
    
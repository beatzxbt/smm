import ccxt.async_support as ccxt
import ccxt.pro as ccxtpro
import numpy as np
from numpy_ringbuffer import RingBuffer
from frameworks.tools.logger import Logger
from frameworks.tools.orderbook import Orderbook
from typing import Tuple, List, Dict, Coroutine

custom_clients = [
    "binance", 
    "bybit", 
    "hyperliquid",
    # "okx",
    # "kucoin"
]

class SharedState:

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
        self.primary_exchange = ""

    async def load_markets(self, primary_exchange: str, pairs: List[Tuple[str, str]]) -> None:
        """
        Initialize a correct client, market & private dict in the general 
        sharedstate dicts, to be accessible anywhere within the system.

        Parameters
        ----------
        primary_exchange : str
            Exchange the user intends to quote on

        pairs : List[Tuples]
            Contains pairs of (exchange, symbol)

        Returns
        -------
        None
        """
        self.primary_exchange = primary_exchange

        for pair in pairs:
            primary = pair[0] == self.primary_exchange
            self._create_client_pair_(pair, primary)
            self._create_market_pair_(pair, primary)
            self._create_private_pair_(pair, primary)
            await self._initialize_(pair)
        
    def _create_market_pair_(self, pair: Tuple[str, str]) -> Dict:
        exchange, symbol = self._pair_to_lower_(pair)

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

    def _create_private_pair_(self, pair: Tuple[str, str], primary: bool=False) -> Dict:
        exchange, symbol = self._pair_to_lower_(pair)

        if not primary:
            return True

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
            "executions": RingBuffer(1000, dtype=(float, 10)),

            "currentPosition": {},
            "leverage": None
        }

    def _create_client_pair_(self, pair: Tuple[str, str], primary: bool=False) -> Dict:
        exchange, _ = self._pair_to_lower_(pair)

        # Exchange client already initialized...
        if exchange in self.clients:
            return None

        try:
            if exchange in custom_clients:
                # TODO: Initialize custom exchange, using dependency injection within the client
                order_client = getattr("brrrclient_rest", exchange)
                ws_client = getattr("brrrclient_ws", exchange)

            else:
                order_client = getattr(ccxt, exchange)
                ws_client = getattr(ccxtpro, exchange)  
                # TODO: Add key/secret startup for CCXT clients

        except Exception as e:
            self.logging.critical(f"Error initializing {exchange}: {e}")
            raise e

        self.clients[exchange] = {
            "order_client": order_client,
            "ws_client": ws_client
        }
    
    async def _initialize_(self, pair: Tuple[str, str], primary: bool=False) -> Coroutine:
        """
        Run initialization tasks on each pair, pulling:  

        -> Acquire user's maker/taker fees information
        -> Acquire user's rate limits
        -> Establishing the TCP connection to server (ping) 
        -> Acquire symbol's tick/lot sizes
        -> Fill all relevant market data points (trades/ob/ohlcv)

        If the pair is not a primary exchange, then only the final 
        two tasks are ran...

        Parameters
        ----------
        pair : Tuple[str, str]
            (exchange, symbol)

        Returns
        -------
        Coroutine
        """
        await self.clients[pair[0]]["order_client"].initialize(primary)

    def _pair_to_lower_(self, pair: Tuple[str, str]) -> Tuple[str, str]:
        return tuple(i.lower() for i in pair)
    
import numpy as np
import ccxt
import ccxt.async_support as ccxt
import ccxt.pro as ccxtpro
from numpy_ringbuffer import RingBuffer
from numpy.typing import NDArray
from typing import Tuple, List, Dict
from frameworks.tools.logger import Logger
from frameworks.tools.common.orderbook import Orderbook

custom_clients = [
    "binance", 
    "bybit", 
    "hyperliquid"
]

class SharedState:

    def __init__(self, pairs: List[Tuple[str, str]]) -> None:
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

        for pair in pairs:
            self._initialize_client_pair_(pair)
            self._initialize_market_pair_(pair)
            self._initialize_private_pair_(pair)
    
    def _initialize_market_pair_(self, pair: Tuple[str, str]) -> Dict:
        exchange, symbol = self._pair_to_lower_(pair)

        if exchange not in self.market:
            self.market[exchange] = {}
        
        self.market[exchange][symbol] = {
            "book": Orderbook(),
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

    def _initialize_private_pair_(self, pair: Tuple[str, str]) -> Dict:
        exchange, symbol = self._pair_to_lower_(pair)

        if exchange not in self.private:
            self.private[exchange] = {
                "API": {
                    "key": None,
                    "secret": None,
                    "rateLimits": {}, # TODO: Populated by OMS
                    "takerFees": None, # TODO: Initialized by OMS
                    "makerFees": None, # TODO: Initialized by OMS
                }
            }
        
        self.private[exchange][symbol] = {
            "openOrders": {},
            "executions": RingBuffer(1000, dtype=(float, 10)),

            "currentPosition": None,
            "currentUPnl": None,
            "currentBalance": None,
            "leverage": None
        }

    def _initialize_client_pair_(self, pair: Tuple[str, str]) -> Dict:
        exchange, _ = self._pair_to_lower_(pair)

        # Exchange client already initialized...
        if exchange in self.clients:
            return None

        try:
            if exchange in ["binance", "bybit", "hyperliquid"]:
                # TODO: Initialize custom exchange, using dependency injection within the client
                order_client = getattr("brrrclient_rest", exchange)
                ws_client = getattr("brrrclient_ws", exchange)

            else:
                order_client = getattr(ccxt, exchange)
                ws_client = getattr(ccxtpro, exchange)  

        except Exception as e:
            self.logging.critical(f"Error initializing {exchange}: {e}")
            raise e

        self.clients[exchange] = {
            "order_client": order_client,
            "ws_client": ws_client
        }
    
    def _pair_to_lower_(self, pair: Tuple[str, str]) -> Tuple[str, str]:
        return tuple(i.lower() for i in pair)
    
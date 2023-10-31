
import asyncio
import numpy as np
import yaml
from collections import deque
from numpy_ringbuffer import RingBuffer

from exchange.binance.websockets.handlers.orderbook import OrderBookBinance
from exchange.bybit.websockets.handlers.orderbook import OrderBookBybit


class MarketDataSharedState:


    def __init__(self, config_dir: str, param_dir: str) -> None:
        self.binance_symbols = [] # Fix import logic here
        self.bybit_symbols = [] # Fix import logic here

        self.binance = {f"{symbol}": self._base_data_outline() for symbol in self.binance_symbols}
        self.binance["book"] = OrderBookBinance()

        self.bybit = {f"{symbol}": self._base_data_outline() for symbol in self.bybit_symbols}
        self.bybit["book"] = OrderBookBybit()

    
    def _base_data_outline(self):
        """
        Base dict for all exchange market data

        Values with 'None' will be populated in '__init__'
        """

        return {
            "trades": RingBuffer(capacity=1000, dtype=(float, 4)),
            "klines": RingBuffer(capacity=1000, dtype=(float, 7)),
            "bba": np.ones((2, 2)), # [Bid[P, Q], Ask[P, Q]]
            "liquidations": RingBuffer(capacity=1000, dtype=(float, 5)),
            "book": None, 

            "mark_price": 0,
            "index_price": 0,
            "last_price": 0,
            "mid_price": 0,
            "wmid_price": 0,
            "funding_rate": 0,
            "volume_24h": 0,

            "tick_size": 0,
            "lot_size": 0
        }

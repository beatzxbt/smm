import asyncio
import numpy as np
import yaml
from collections import deque
from numpy_ringbuffer import RingBuffer
from typing import Dict, Coroutine
from numpy.typing import NDArray
from src.exchanges.common.localorderbook import BaseOrderBook
from src.exchanges.binance.websockets.handlers.orderbook import OrderBookBinance
from src.exchanges.bybit.websockets.handlers.orderbook import OrderBookBybit


class SharedState:
    CONFIG_DIR = "/Users/beatz/Documents/Github/bybit-smm/config/bybit.yaml"  
    PARAM_DIR = "/Users/beatz/Documents/Github/bybit-smm/src/parameters.yaml"  

    def __init__(self) -> None:
        if not self.CONFIG_DIR or not self.PARAM_DIR:
            raise ValueError("Missing config and/or param directories!")

        self.load_config()
        self.load_initial_settings()

        # Binance attributes
        self.binance_ws_connected = False
        self.binance_trades = RingBuffer(capacity=1000, dtype=(float, 4))
        self.binance_bba = np.ones((2, 2), dtype=np.float64)
        self.binance_book = OrderBookBinance()
        self.binance_last_price = 0

        # Bybit attributes
        self.bybit_ws_connected = False
        self.bybit_klines = RingBuffer(capacity=500, dtype=(float, 7))
        self.bybit_trades = RingBuffer(capacity=1000, dtype=(float, 4))
        self.bybit_bba = np.ones((2, 2), dtype=np.float64)
        self.bybit_book = OrderBookBybit()
        self.bybit_mark_price = 0

        # Other attributes
        self.current_orders = {}
        # self.execution_feed = deque(maxlen=100) # NOTE: Unused
        self.volatility_value = 0
        self.inventory_delta = 0

    def load_config(self) -> None:
        with open(self.CONFIG_DIR, "r") as f:
            config = yaml.safe_load(f)
            self.api_key = config["api_key"]
            self.api_secret = config["api_secret"]

            if not self.api_key or not self.api_secret:
                raise ValueError("Missing API key and/or secret!")

    def load_settings(self, settings: Dict) -> None:
        self.primary_data_feed = str(settings["primary_data_feed"]).upper()
        self.binance_symbol = str(settings["binance_symbol"])
        self.bybit_symbol = str(settings["bybit_symbol"])
        self.account_size = float(settings["account_size"])
        self.bb_length = int(settings["bollinger_band_length"])
        self.bb_std = int(settings["bollinger_band_std"])
        self.quote_offset = float(settings["quote_offset"])
        self.size_offset = float(settings["size_offset"])
        self.volatility_offset = float(settings["volatility_offset"])
        self.base_spread = float(settings["base_spread"])
        self.min_order_size = float(settings["min_order_size"])
        self.max_order_size = float(settings["max_order_size"])
        self.inventory_extreme = float(settings["inventory_extreme"])

    def load_initial_settings(self) -> None:
        with open(self.PARAM_DIR, "r") as f:
            settings = yaml.safe_load(f)
            self.load_settings(settings)

    async def refresh_parameters(self) -> Coroutine:
        while True:
            await asyncio.sleep(60)
            with open(self.PARAM_DIR, "r") as f:
                settings = yaml.safe_load(f)
                self.load_settings(settings)

    @property
    def binance_mid(self) -> float:
        return self.calculate_mid(self.binance_bba)

    @property
    def binance_wmid(self) -> float:
        return self.calculate_wmid(self.binance_bba)

    @property
    def binance_vamp(self) -> float:
        return self.calculate_vamp(self.binance_book)
    
    @property
    def bybit_mid(self) -> float:
        return self.calculate_mid(self.bybit_bba)

    @property
    def bybit_wmid(self) -> float:
        return self.calculate_wmid(self.bybit_bba)
    
    @property
    def bybit_vamp(self) -> float:
        return self.calculate_vamp(self.bybit_book)

    @staticmethod
    def calculate_mid(bba: NDArray) -> float:
        best_bid, best_ask = bba[0][0], bba[1][0]
        return (best_ask + best_bid)/2

    @staticmethod
    def calculate_wmid(bba: NDArray) -> float:
        imb = bba[0][1] / (bba[0][1] + bba[1][1])
        return bba[1][0] * imb + bba[0][0] * (1 - imb)
    
    @staticmethod
    def calculate_vamp(book: BaseOrderBook, depth=10) -> float:
        bids_qty_sum = sum(bid[1] for bid in book.bids[:depth])
        asks_qty_sum = sum(ask[1] for ask in book.asks[:depth])
        bid_fair = sum(bid[0] * (bid[1] / bids_qty_sum) for bid in book.bids[:depth])
        ask_fair = sum(ask[0] * (ask[1] / asks_qty_sum) for ask in book.asks[:depth])
        return (bid_fair + ask_fair) / 2
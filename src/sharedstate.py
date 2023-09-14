
import asyncio
import numpy as np
import yaml
from collections import deque
from numpy_ringbuffer import RingBuffer

from src.exchanges.binance.websockets.handlers.orderbook import OrderBookBinance
from src.exchanges.bybit.websockets.handlers.orderbook import OrderBookBybit


class SharedState:

    CONFIG_DIR = ""  
    PARAM_DIR = ""  

    def __init__(self) -> None:

        if len(self.CONFIG_DIR) == 0 or len(self.PARAM_DIR) == 0:
            raise ValueError("Missing CONFIG/PARAM paths!")

        self.load_config()
        self.load_initial_settings()

        # Binance attributes
        self.binance_trades = RingBuffer(capacity=1000, dtype=(float, 4))
        self.binance_bba = np.ones((2, 2))  # [Bid[P, Q], Ask[P, Q]]
        self.binance_book = OrderBookBinance()
        self.binance_last_price = 0

        # Bybit attributes
        self.bybit_trades = RingBuffer(capacity=1000, dtype=(float, 4))
        self.bybit_bba = np.ones((2, 2))  # [Bid[P, Q], Ask[P, Q]]
        self.bybit_book = OrderBookBybit()
        self.bybit_mark_price = 0
        self.bybit_klines = RingBuffer(capacity=500, dtype=(float, 7))

        # Other attributes
        self.current_orders = {}
        self.execution_feed = deque(maxlen=100)
        self.volatility_value = 0
        self.inventory_delta = 0


    def load_config(self):
        with open(self.CONFIG_DIR, "r") as f:
            config = yaml.safe_load(f)
            self.api_key = config["api_key"]
            self.api_secret = config["api_secret"]

            if len(self.api_key) == 0 or len(self.api_secret) == 0:
                raise ValueError("Missing API key/secret!")


    def load_settings(self, settings):
        self.binance_symbol = str(settings["binance_symbol"])
        self.bybit_symbol = str(settings["bybit_symbol"])
        self.binance_tick_size = float(settings["binance_tick_size"])
        self.binance_lot_size = float(settings["binance_lot_size"])
        self.bybit_tick_size = float(settings["bybit_tick_size"])
        self.bybit_lot_size = float(settings["bybit_lot_size"])
        self.primary_data_feed = str(settings["primary_data_feed"]).upper()
        self.account_size = float(settings["account_size"])
        self.buffer = float(settings["buffer"]) * self.bybit_tick_size
        self.bb_length = int(settings["bollinger_band_length"])
        self.bb_std = int(settings["bollinger_band_std"])
        self.quote_offset = float(settings["quote_offset"])
        self.size_offset = float(settings["size_offset"])
        self.volatility_offset = float(settings["volatility_offset"])
        self.base_spread = float(settings["base_spread"])
        self.num_orders = int(settings["number_of_orders"])
        self.min_order_size = float(settings["min_order_size"])
        self.max_order_size = float(settings["max_order_size"])
        self.inventory_extreme = float(settings["inventory_extreme"])


    def load_initial_settings(self):
        with open(self.PARAM_DIR, "r") as f:
            settings = yaml.safe_load(f)
            self.load_settings(settings)


    async def refresh_parameters(self):
        while True:
            with open(self.PARAM_DIR, "r") as f:
                settings = yaml.safe_load(f)
                self.load_settings(settings)

            await asyncio.sleep(60)


    @property
    def binance_mid_price(self):
        return self.calculate_mid_price(self.binance_bba)


    @property
    def binance_weighted_mid_price(self):
        return self.calculate_weighted_mid_price(self.binance_bba)


    @property
    def bybit_mid_price(self):
        return self.calculate_mid_price(self.bybit_bba)


    @property
    def bybit_weighted_mid_price(self):
        return self.calculate_weighted_mid_price(self.bybit_bba)


    @staticmethod
    def calculate_mid_price(bba):
        best_bid, best_ask = bba[0][0], bba[1][0]
        return (best_ask + best_bid)/2


    @staticmethod
    def calculate_weighted_mid_price(bba):
        imb = bba[0][1] / (bba[0][1] + bba[1][1])
        return bba[1][0] * imb + bba[0][0] * (1 - imb)
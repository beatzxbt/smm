import asyncio
import numpy as np
import os
import yaml
from collections import deque
from numpy_ringbuffer import RingBuffer
from typing import Dict
from numpy.typing import NDArray
from src.exchanges.common.localorderbook import BaseOrderBook
from src.exchanges.binance.websockets.handlers.orderbook import OrderBookBinance
from src.exchanges.bybit.websockets.handlers.orderbook import OrderBookBybit

class SharedState:
    """
    Centralizes shared data and configurations for the trading application, including market data
    and trading parameters, and provides utility methods for market metric calculations.

    Attributes
    ----------
    PARAM_DIR : str
        The directory path to the parameters file containing trading settings.

    Methods
    -------
    load_settings(settings: Dict) -> None:
        Updates trading parameters and settings from a given dictionary.
    load_initial_settings() -> None:
        Loads initial trading settings from the parameters file.
    refresh_parameters() -> Coroutine:
        Asynchronously refreshes trading parameters from the parameters file at regular intervals.
    calculate_mid(bba: NDArray) -> float:
        Calculates the mid-price from the best bid and ask prices.
    calculate_wmid(bba: NDArray) -> float:
        Calculates the weighted mid-price based on best bid and ask quantities.
    calculate_vamp(book: BaseOrderBook, depth=10) -> float:
        Calculates the volume-weighted average mid-price (VAMP) based on the specified depth.
    """

    PARAM_PATH = os.path.dirname(os.path.realpath(__file__)) + "/../parameters.yaml"  

    def __init__(self) -> None:
        """
        Initializes the SharedState with paths to configuration and parameters files,
        loads initial configurations and settings, and initializes market data attributes.
        """
        self.api_key = os.getenv("API_KEY")
        self.api_secret = os.getenv("API_SECRET")
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing API key and/or secret!")

        if not self.PARAM_PATH:
            raise ValueError("Missing config and/or param directories!")
        self._load_initial_settings_()

        # Initialize market data attributes for Binance and Bybit
        self.binance_ws_connected = False
        self.binance_trades = RingBuffer(capacity=1000, dtype=(float, 4))
        self.binance_bba = np.ones((2, 2), dtype=np.float64)
        self.binance_book = OrderBookBinance()
        self.binance_last_price = 0

        self.bybit_ws_connected = False
        self.bybit_klines = RingBuffer(capacity=500, dtype=(float, 7))
        self.bybit_trades = RingBuffer(capacity=1000, dtype=(float, 4))
        self.bybit_bba = np.ones((2, 2), dtype=np.float64)
        self.bybit_book = OrderBookBybit()
        self.bybit_mark_price = 0

        # Other shared attributes
        self.current_orders = {}
        self.execution_feed = deque(maxlen=100)
        self.volatility_value = 0
        self.inventory_delta = 0


    def _load_settings_(self, settings: Dict) -> None:
        """
        Updates trading parameters and settings from a dictionary of settings.
        """
        self.primary_data_feed = str(settings["primary_data_feed"]).upper()
        self.binance_symbol = str(settings["binance_symbol"])
        self.bybit_symbol = str(settings["bybit_symbol"])
        self.account_size = float(settings["account_size"])
        self.bb_length = int(settings["bollinger_band_length"])
        self.bb_std = int(settings["bollinger_band_std"])
        self.price_offset = float(settings["price_offset"])
        self.size_offset = float(settings["size_offset"])
        self.volatility_offset = float(settings["volatility_offset"])
        self.base_spread = float(settings["base_spread"])
        self.min_order_size = float(settings["min_order_size"])
        self.max_order_size = float(settings["max_order_size"])
        self.inventory_extreme = float(settings["inventory_extreme"])

    def _load_initial_settings_(self) -> None:
        """
        Loads initial trading settings from the parameters YAML file.
        """
        with open(self.PARAM_PATH, "r") as f:
            settings = yaml.safe_load(f)
            self._load_settings_(settings)

    async def refresh_parameters(self) -> None:
        """
        Periodically refreshes trading parameters from the parameters file.
        """
        while True:
            await asyncio.sleep(10)  # Refresh every 10 seconds
            with open(self.PARAM_PATH, "r") as f:
                settings = yaml.safe_load(f)
                self._load_settings_(settings)

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
        """
        Calculates the mid-price from the best bid and ask prices.

        Steps:
        1. Extract the best bid price (bba[0][0]) and the best ask price (bba[1][0]) from the bba array.
        2. Calculate the mid-price as the average of the best bid and ask prices.

        Parameters
        ----------
        bba : NDArray
            A NumPy array containing the best bid and ask prices and quantities. The expected shape is (2, 2).

        Returns
        -------
        float
            The calculated mid-price.
        """
        best_bid, best_ask = bba[0][0], bba[1][0]
        return (best_ask + best_bid) / 2

    @staticmethod
    def calculate_wmid(bba: NDArray) -> float:
        """
        Calculates the weighted mid-price considering the quantities of the best bid and ask.

        Steps:
        1. Calculate the bid-ask imbalance by dividing the best bid quantity by the sum of best bid and ask quantities.
        2. Compute the weighted mid-price by applying the imbalance to the best bid and ask prices.

        Parameters
        ----------
        bba : NDArray
            A NumPy array containing the best bid and ask prices and quantities. The expected shape is (2, 2).

        Returns
        -------
        float
            The calculated weighted mid-price, factoring in the bid-ask imbalance.
        """
        imb = bba[0][1] / (bba[0][1] + bba[1][1])
        return bba[1][0] * imb + bba[0][0] * (1 - imb)

    @staticmethod
    def calculate_vamp(book: BaseOrderBook, depth=10) -> float:
        """
        Calculates the Volume-Weighted Average Mid-Price (VAMP) over a specified depth from the order book.

        Steps:
        1. Sum the quantities for the top `depth` bids and asks separately.
        2. Calculate the weighted price for each bid and ask up to the specified depth, using their quantities as weights.
        3. Compute the fair value for bids and asks by multiplying each price by its relative weight and summing the results.
        4. Calculate the VAMP as the average of the bid and ask fair values.

        Parameters
        ----------
        book : BaseOrderBook
            An instance of BaseOrderBook containing the current state of the order book.
        depth : int, optional
            The depth of the order book to consider for the calculation, by default 10.

        Returns
        -------
        float
            The calculated VAMP, representing an average price adjusted for volume at each depth level.
        """
        bids_qty_sum = sum(bid[1] for bid in book.bids[:depth])
        asks_qty_sum = sum(ask[1] for ask in book.asks[:depth])
        bid_fair = sum(bid[0] * (bid[1] / bids_qty_sum) for bid in book.bids[:depth])
        ask_fair = sum(ask[0] * (ask[1] / asks_qty_sum) for ask in book.asks[:depth])

        return (bid_fair + ask_fair) / 2
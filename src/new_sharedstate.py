import tomli
import numpy as np
from numpy_ringbuffer import RingBuffer
from collections import deque

from src.exchanges.binance.websockets.handlers.orderbook import OrderBookBinance
from src.exchanges.bybit.websockets.handlers.orderbook import OrderBookBybit

class NewSharedState:

    def __init__(
        self,
        #All the default argumentes are defined in the parser arguments (main.py)
        key_arg,
        ticker_arg,
        feed_arg,
        sizef_arg,
        size_arg,
        algo_arg,
        conf_arg
    ) -> None:
        self.load_config(
            key_arg
        )
        self.load_settings(
            ticker_arg,
            feed_arg,
            sizef_arg,
            size_arg,
            algo_arg,
            conf_arg
        )

        # Initialize non-user-configurable data structures

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

        None


    def load_config(self, key_arg):
        with open("config/bybit.toml", "rb") as f:
            config = tomli.load(f)
            self.api_key = self.get_config_value(config["api_key"], key_arg, "api_key")
            self.api_secret = self.get_config_value(config["api_key"], key_arg, "api_secret")

    def load_settings(
        self, 
        ticker_arg,
        feed_arg,
        sizef_arg,
        size_arg,
        algo_arg,
        conf_arg
    ):

        with open("config/config.toml", "rb") as f:
            settings = tomli.load(f)
            #Binance symbol
            self.binance_symbol = self.get_config_value(settings["binance_symbol"], ticker_arg, "symbol")
            self.binance_tick_size = self.get_config_value(settings["binance_symbol"], ticker_arg, "tick_size")
            self.binance_lot_size = self.get_config_value(settings["binance_symbol"], ticker_arg, "lot_size")
            #Bybit symbol
            self.bybit_symbol = self.get_config_value(settings["bybit_symbol"], ticker_arg, "symbol")
            self.bybit_tick_size = self.get_config_value(settings["bybit_symbol"], ticker_arg, "tick_size")
            self.bybit_lot_size = self.get_config_value(settings["bybit_symbol"], ticker_arg, "lot_size")
            #Primary date feed
            self.primary_data_feed = self.get_config_value(settings["data_feed"], feed_arg, "feed")  
            #Buffer
            self.buffer = int(self.get_config_value(settings["buffer"], None, "buffer"))
            #Account size
            if size_arg is not None:
                self.account_size = int(size_arg)
            else:
                self.account_size = int(self.get_config_value(settings["account"], sizef_arg, "size"))
            #Volatility indicator
            self.bb_length = int(self.get_config_value(settings["volatility"], None, "bollinger_band_length"))
            self.bb_std = int(self.get_config_value(settings["volatility"], None, "bollinger_band_std"))
            #Master offsets
            self.quote_offset = float(self.get_config_value(settings["offsets"], None, "quote_offset"))
            self.size_offset = float(self.get_config_value(settings["offsets"], None, "size_offset"))
            self.volatility_offset = float(self.get_config_value(settings["offsets"], None, "volatility_offset"))
            #Strategy
            self.strategy = self.get_config_value(settings["strategy"], algo_arg, "strategy")
            self.strategy_config = self.get_strat_configuration(settings["strategies"], self.strategy, conf_arg)
            print(self.strategy)
            print(self.strategy_config)

    
    def get_config_value(self, arr, arg, key):
        """
        Retrieve a configuration value from a JSON array.

        This function retrieves a configuration value based on the specified arguments.
        
        Args:
            arr (dict): The JSON array containing configuration settings.
            arg (str): The specific category within the array. Use None for default settings.
            key (str): The key corresponding to the setting to retrieve.

        Returns:
            The value corresponding to the specified key in the configuration.


        """
        if arg is None:
            default_config = arr.get("default")
            if default_config and key in default_config:
                return default_config[key]
            else:
                raise ValueError("There is no default configuration or the key does not exist.")
        else:
            specific_config = arr.get(arg)
            if specific_config and key in specific_config:
                return specific_config[key]
            else:
                raise ValueError(f"There is no configuration for '{arg}' or the key does not exist.")

    def get_strat_configuration(self, arr, strat_name, arg):
        """
        Get configuration settings for a specific strategy.

        Args:
            arr (dict): The configuration dictionary.
            strat_name (str): The name of the strategy.
            arg (str): The optional argument to select a specific configuration.

        Returns:
            dict: The configuration settings for the specified strategy and argument.
        """

        if strat_name in arr:
            config = arr[strat_name]
            if config is None:
                raise ValueError(f"The configuration for '{strat_name}' strategy is None.")
            if arg is None:
                default_config = config.get("default")
                if default_config is None:
                    raise ValueError(f"The default configuration for '{strat_name}' strategy is None.")
                return default_config
            else:
                specific_config = config.get(arg)
                if specific_config is None:
                    raise ValueError(f"The {arg} configuration for '{strat_name}' strategy is None")
        else:
            raise ValueError(f"There is no configuration for '{strat_name}' strategy.")

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

import yaml
import asyncio
import numpy as np

from src.binance.websockets.handlers.orderbook import LocalOrderBook as BinanceBook
from src.bybit.websockets.handlers.orderbook import LocalOrderBook as BybitBook


config_dir = "/Users/vishva/Documents/GitHub/bybit-smm/config/bybit.yaml"
param_dir = "/Users/vishva/Documents/GitHub/bybit-smm/src/parameters.yaml"


class SharedState:


    def __init__(self) -> None:
        
        # Load initial config \
        with open(config_dir, "r") as f:
            config = yaml.safe_load(f)
            self.api_key = config['api_key']
            self.api_secret = config['api_secret']

        # Load initial settings \
        with open(param_dir, "r") as f:
            settings = yaml.safe_load(f)

            # Initialize parameters \
            self.binance_symbol = settings['binance_symbol']
            self.binance_tick_size = float(settings['binance_tick_size'])
            self.binance_lot_size = float(settings['binance_lot_size'])

            self.bybit_symbol = settings['bybit_symbol']
            self.bybit_tick_size = float(settings['bybit_tick_size'])
            self.bybit_lot_size = float(settings['bybit_lot_size'])

            # Primary data feed #
            self.primary_data_feed = settings['primary_data_feed']

            self.buffer_multiplier = int(settings['buffer_multiplier']) * self.bybit_tick_size
            self.account_size = float(settings['account_size'])

            self.bb_length = int(settings['bollinger_band_length'])
            self.bb_std = int(settings['bollinger_band_std'])

            self.quote_offset = float(settings['quote_offset'])
            self.size_offset = float(settings['size_offset'])
            self.volatility_offset = float(settings['volatility_offset'])

            self.target_spread = float(settings['target_spread'])
            self.num_orders = int(settings['number_of_orders'])
            self.minimum_order_size = float(settings['minimum_order_size'])
            self.maximum_order_size = float(settings['maximum_order_size'])

            self.inventory_extreme = float(settings['inventory_extreme'])

        self.binance_trades = []
        self.binance_bba = np.array([[1., 1.], [1., 1.]]) # [Bid[P, Q], Ask[P, Q]
        self.binance_book = BinanceBook()
        self.binance_last_price = 1.

        self.bybit_trades = []
        self.bybit_bba = np.array([[1., 1.], [1., 1.]]) # [Bid[P, Q], Ask[P, Q]
        self.bybit_book = BybitBook()
        self.bybit_mark_price = 1.
        self.bybit_klines = []

        self.position_feed = []
        self.execution_feed = {}

        self.volatility_value = 1.
        self.alpha_value = 0.
        self.inventory_delta = 0.

    
    async def refresh_parameters(self):

        while True:

            # Reload configuration from YAML file \
            with open(param_dir, "r") as f:
                settings = yaml.safe_load(f)

                # Update parameters \
                self.buffer_multiplier = int(settings['buffer_multiplier']) * self.bybit_tick_size
                self.account_size = float(settings['account_size'])

                self.bb_length = int(settings['bollinger_band_length'])
                self.bb_std = int(settings['bollinger_band_std'])

                self.quote_offset = float(settings['quote_offset'])
                self.size_offset = float(settings['size_offset'])
                self.volatility_offset = float(settings['volatility_offset'])

                self.target_spread = float(settings['target_spread'])
                self.num_orders = int(settings['number_of_orders'])
                self.minimum_order_size = float(settings['minimum_order_size'])
                self.maximum_order_size = float(settings['maximum_order_size'])

                self.inventory_extreme = float(settings['inventory_extreme'])

            # Refresh every 60s \
            await asyncio.sleep(60)


    @property
    def binance_mid_price(self):
        best_bid = self.binance_bba[0][0]
        best_ask = self.binance_bba[1][0]

        return float((best_ask - best_bid) + best_bid)


    @property
    def bybit_mid_price(self):
        best_bid = self.bybit_bba[0][0]
        best_ask = self.bybit_bba[1][0]

        return float((best_ask - best_bid) + best_bid)


import asyncio
import websockets
import json
import yaml
import numpy as np

from src.bybit.websockets import PublicWs, PrivateWs, PrivateWsHandler
from src.bybit.orders import Order
from src.bybit.client import HTTP_PublicRequests
from src.strategy import Inventory, Strategy
from src.indicators.simple_range import simple_range


class Main:


    def __init__(self, symbol: str, config_dir: str, param_dir: str) -> None:

        self.symbol = symbol
        self.param_dir = param_dir
        self.config_dir = config_dir

        # Load initial config \
        with open(self.config_dir, "r") as f:
            config = yaml.safe_load(f)
            self.api_key = config['api_key']
            self.api_secret = config['api_secret']

        # Load initial settings \
        with open(self.param_dir, "r") as f:
            settings = yaml.safe_load(f)
            self.tick_size = settings['tick_size']
            self.lot_size = settings['lot_size']
            self.buffer_multiplier = settings['buffer_multiplier'] * self.tick_size
            self.account_size = settings['account_size']
            self.quote_offset = settings['quote_offset']
            self.size_offset = settings['size_offset']
            self.target_spread = settings['target_spread']
            self.num_orders = settings['number_of_orders']
            self.volatility_offset = settings['volatility_offset']
            self.minimum_order_size = settings['minimum_order_size']
            self.maximum_order_size = settings['maximum_order_size']
            self.inventory_neutral = settings['inventory_neutral']
            self.inventory_extreme = settings['inventory_extreme']

        # Initialize local variables \
        self.mark_price = 1.0
        self.best_bid_price = self.mark_price - self.tick_size
        self.best_ask_price = self.mark_price + self.tick_size
        self.inventory_delta = 0.0
        self.volatility_value = 1.0


    # Function that updates configuration every few {sleep_duration} minutes \
    async def refresh_parameters(self, sleep_duration: int):

        while True:

            # Reload configuration from YAML file \
            with open(self.param_dir, "r") as f:
                config = yaml.safe_load(f)

            # Update parameters \
            self.tick_size = config['tick_size']
            self.lot_size = config['lot_size']
            self.buffer_multiplier = config['buffer_multiplier'] * self.tick_size
            self.account_size = config['account_size']
            self.quote_offset = config['quote_offset']
            self.size_offset = config['size_offset']
            self.target_spread = config['target_spread']
            self.num_orders = config['number_of_orders']
            self.volatility_offset = config['volatility_offset']
            self.minimum_order_size = config['minimum_order_size']
            self.maximum_order_size = config['maximum_order_size']
            self.inventory_neutral = config['inventory_neutral']
            self.inventory_extreme = config['inventory_extreme']

            # Refresh rate interval \
            await asyncio.sleep(sleep_duration*60)


    # Function that updates inventory delta after every order execution \
    # It also prints out all filled orders to the terminal \
    async def account_stats_feed(self):

        websocket_stream = 'wss://stream.bybit.com/v5/private'

        async for websocket in websockets.connect(websocket_stream):
            
            try:
                req, topics = PrivateWs(self.api_key, self.api_secret).multi_stream_request(['Position', 'Order'])

                _auth = await websocket.send(PrivateWs(self.api_key, self.api_secret).auth())
                print('Successfully authenticated to account private feed...')

                _sub = await websocket.send(req)
                print('Subscribed to {} feeds...'.format(topics))

                while True:

                    recv = json.loads(await websocket.recv())
                    
                    if 'success' in recv:
                        pass

                    elif recv['data'][0]['symbol'] == self.symbol:

                        data = recv['data']

                        # Generating inventory delta from position feed updates \
                        if recv['topic'] == topics[0]:
                            
                            self.inventory_delta = Inventory(data[-1]).calculate_delta(self.account_size)
                            # Add TWAP logic here, it should not be extremely large, just enough to get it below limits 
                            # Make sure there is some checker so multiple TWAPs dont activate accidentally!

                        # Printing live order information to terminal \
                        if recv['topic'] == topics[1]:
                            _print = PrivateWsHandler().print_order_updates(data)

            except websockets.ConnectionClosed:
                continue


    # Function that updates volatility every few seconds using klines \
    async def volatility_feed(self, interval: str, lookback: int, norm_passes: int):
        
        # Initialize the klines array with close prices \
        # Websocket will add onto this list each time a candle is closed \
        klines = await HTTP_PublicRequests().klines(self.symbol, interval)
        klines_hl = klines[['High', 'Low']].to_numpy(dtype=np.float64)

        websocket_stream = 'wss://stream.bybit.com/v5/public/linear'

        async for websocket in websockets.connect(websocket_stream):

            try:
                req, topics = PublicWs(self.symbol).multi_stream_request(['Kline'], interval=interval)
                _sub = await websocket.send(req)
                print('Subscribed to {} feeds...'.format(topics))

                while True:

                    recv = json.loads(await websocket.recv())
                    
                    if 'success' in recv:
                        pass
                    
                    elif recv['topic'] == topics[0]:
                        # This is processing klines updates \
                        # Used to attain close values and calculate volatility \
                        # If candle close, shift array -1 and add new value \
                        # Otherwise, update the most recent candle close value \

                        klines_data = recv['data']

                        for candle in klines_data:
                            new_hl = np.array([float(candle['high']), float(candle['low'])], dtype=np.float64)

                            if candle['confirm'] == True:
                                klines_hl = np.append(arr=klines_hl[1:], values=new_hl.reshape(1, 2), axis=0)

                            else:
                                klines_hl[-1] = new_hl
                            
                            self.volatility_value = simple_range(
                                arr_in = klines_hl, 
                                lookback = lookback, 
                                norm_passes = norm_passes
                            )

                            self.volatility_value += self.volatility_offset

            except websockets.ConnectionClosed:
                continue
                

    # Function that updates mark price and BBA value after every ticker update \
    # Also runs the strategy anytime mark price changes \
    async def strategy(self):
        
        websocket_stream = 'wss://stream.bybit.com/v5/public/linear'

        async for websocket in websockets.connect(websocket_stream):

            try:
                req, topics = PublicWs(self.symbol).multi_stream_request(['Ticker'])
                _sub = await websocket.send(req)
                print('Subscribed to {} feeds...'.format(topics))

                # Start all async futures, updating all global vars in the background \
                _refreshparams = asyncio.create_task(self.refresh_parameters(0.1))
                _accountfeed = asyncio.create_task(self.account_stats_feed())
                _volatilityfeed = asyncio.create_task(self.volatility_feed('5', 10, 0))
                _sleep = await asyncio.sleep(2) # Small timeout to let feeds warm up with data 

                while True:

                    recv = json.loads(await websocket.recv())
                    
                    if 'success' in recv:
                        pass
                    
                    elif recv['topic'] == topics[0]:
                        # This is processing ticker updates \
                        # Used to attain spread and mark price \
                        
                        ticker_data = recv['data']

                        if 'bid1Price' in ticker_data:
                            self.best_bid_price = float(ticker_data['bid1Price'])

                        if 'ask1Price' in ticker_data:
                            self.best_ask_price = float(ticker_data['ask1Price'])

                        if 'markPrice' in ticker_data:
                            new_mark_price = float(ticker_data['markPrice'])
                            
                            current_mark_lower = self.mark_price - self.buffer_multiplier
                            current_mark_upper = self.mark_price + self.buffer_multiplier

                            # Run the strategy and refresh quotes if the mark price has changed by the sufficient amount \
                            if (new_mark_price > current_mark_upper) or (new_mark_price < current_mark_lower):
                                
                                self.mark_price = new_mark_price

                                _cancel = await Order(self.api_key, self.api_secret, self.symbol).cancel_all()

                                _orders = Strategy(
                                        tick_size=self.tick_size,
                                        lot_size=self.lot_size,
                                        num_orders=self.num_orders,
                                        target_spread=self.target_spread,
                                        minimum_order_size=self.minimum_order_size,
                                        maximum_order_size=self.maximum_order_size,
                                        quote_offset=self.quote_offset,
                                        size_offset=self.size_offset
                                    ).market_maker(
                                        mark_price=self.mark_price,
                                        volatility=self.volatility_value,
                                        bba=(self.best_bid_price, self.best_ask_price),
                                        inventory_delta=self.inventory_delta,
                                        inventory_extreme=self.inventory_extreme
                                )
                                
                                _execution = await Order(self.api_key, self.api_secret, self.symbol).batch_orders(_orders)

            except websockets.ConnectionClosed:
                continue
                        


if __name__ == "__main__":

    # Copy the directory of the param .yaml file and paste it below \
    param_dir = "/Users/vishva/Documents/GitHub/bybit-smm/src/parameters.yaml"
    config_dir = "/Users/vishva/Documents/GitHub/bybit-smm/config/bybit.yaml"
    
    _run = asyncio.run(Main('BTCUSDT', config_dir, param_dir).strategy())





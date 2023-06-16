import asyncio
import websockets
import json
import yaml
import numpy as np

from src.bybit.config import Config
from src.bybit.websockets import PublicWs, PrivateWs
from src.bybit.orders import Order
from src.bybit.client import HTTP_PublicRequests
from src.strategy import Inventory, Strategy
from src.indicators.simple_range import simple_range
from src.utils.rounding import round_step_size


# Function that updates configuration every few {sleep_duration} minutes \
async def refresh_parameters(dir: str, sleep_duration: int):

    global tick_size
    global lot_size
    global account_size
    global quote_offset
    global size_offset
    global target_spread
    global volatility_offset
    global minimum_order_size
    global maximum_order_size
    global inventory_neutral
    global inventory_extreme

    while True:
        # Reload configuration from YAML file \
        with open(dir, "r") as f:
            config = yaml.safe_load(f)

        # Update parameters \
        tick_size = config['tick_size']
        lot_size = config['lot_size']
        account_size = config['account_size']
        quote_offset = config['quote_offset']
        size_offset = config['size_offset']
        target_spread = config['target_spread']
        volatility_offset = config['volatility_offset']
        minimum_order_size = config['minimum_order_size']
        maximum_order_size = config['maximum_order_size']
        inventory_neutral = config['inventory_neutral']
        inventory_extreme = config['inventory_extreme']

        # Refresh rate interval \
        await asyncio.sleep(sleep_duration*60)


# Function that updates inventory delta after order execution \
async def account_stats_feed(symbol: str):

    global account_size
    global inventory_delta

    websocket_stream = 'wss://stream.bybit.com/v5/private'

    async with websockets.connect(websocket_stream) as websocket:
        
        req, topics = PrivateWs(Config().api_key(), Config().api_secret()).multi_stream_request(['Position', 'Order'])

        _auth = await websocket.send(PrivateWs(Config().api_key(), Config().api_secret()).auth())
        print('Successfully authenticated to account private feed...')

        _sub = await websocket.send(req)
        print('Subscribed to {} feeds...'.format(topics))

        while True:

            recv = json.loads(await websocket.recv())
            
            if 'success' in recv:
                pass

            elif recv['data'][0]['symbol'] == symbol:

                data = recv['data']

                if recv['topic'] == topics[0]:
                    # Generating inventory delta from position feed updates \
                    # Add inventory control here \
                    inventory_delta = Inventory(data[-1]).calculate_delta(account_size)

                if recv['topic'] == topics[1]:
                    pass


# Function that updates volatility every few seconds using klines \
async def volatility_feed(symbol: str, interval: str, lookback: int, norm_passes: int):

    global volatility_value
    global volatility_offset
    
    # Initialize the klines array with close prices \
    # Websocket will add onto this list each time a candle is closed \
    klines = await HTTP_PublicRequests().klines(symbol, interval)
    klines_hl = klines[['High', 'Low']].to_numpy(dtype=np.float64)

    websocket_stream = 'wss://stream.bybit.com/v5/public/linear'

    async with websockets.connect(websocket_stream) as websocket:
        req, topics = PublicWs(symbol).multi_stream_request(['Kline'], interval=interval)
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
                    
                    volatility_value = simple_range(
                        arr_in = klines_hl, 
                        lookback = lookback, 
                        norm_passes = norm_passes
                    )

                    volatility_value += volatility_offset
                

# Function that updates mark price and BBA value after every ticker update \
# Also runs the strategy anytime mark price changes \
async def main(symbol: str):

    global inventory_delta
    global volatility_value

    global tick_size
    global lot_size
    global account_size
    global quote_offset
    global size_offset
    global target_spread
    global minimum_order_size
    global maximum_order_size
    global inventory_neutral
    global inventory_extreme
    
    mark_price = 0.
    best_ask_price = 0.
    best_bid_price = 0.

    websocket_stream = 'wss://stream.bybit.com/v5/public/linear'

    async with websockets.connect(websocket_stream) as websocket:
        req, topics = PublicWs(symbol).multi_stream_request(['Ticker'])
        _sub = await websocket.send(req)
        print('Subscribed to {} feeds...'.format(topics))

        # Start all async futures, updating all global vars in the background \
        _refreshparams = asyncio.create_task(refresh_parameters(param_dir, 0.1))
        _accountfeed = asyncio.create_task(account_stats_feed(symbol))
        _volatilityfeed = asyncio.create_task(volatility_feed(symbol, '5', 5, 0))
        _sleep = await asyncio.sleep(1)   # Small timeout to let feeds warm up with data 

        while True:

            recv = json.loads(await websocket.recv())
            
            if 'success' in recv:
                pass
            
            elif recv['topic'] == topics[0]:
                # This is processing ticker updates \
                # Used to attain spread and mark price \
                
                ticker_data = recv['data']

                if 'bid1Price' in ticker_data:
                    best_bid_price = float(ticker_data['bid1Price'])

                if 'ask1Price' in ticker_data:
                    best_ask_price = float(ticker_data['ask1Price'])

                if 'markPrice' in ticker_data:
                    new_mark_price = round_step_size(float(ticker_data['markPrice']), tick_size)
                    
                    # Run the strategy and refresh quotes if the mark price has changed \
                    if new_mark_price == mark_price:
                        pass

                    else:
                        mark_price = new_mark_price

                        _cancel = await Order(Config().api_key(), Config().api_secret(), symbol).cancel_all()

                        _orders = Strategy(
                                tick_size=tick_size,
                                lot_size=lot_size,
                                target_spread=target_spread,
                                minimum_order_size=minimum_order_size,
                                maximum_order_size=maximum_order_size,
                                quote_offset=quote_offset,
                                size_offset=size_offset
                            ).market_maker(
                                mark_price=mark_price,
                                volatility=volatility_value,
                                bba=(best_bid_price, best_ask_price),
                                inventory_delta=inventory_delta,
                                inventory_extreme=inventory_extreme
                        )
                        
                        _execution = await Order(Config().api_key(), Config().api_secret(), symbol).batch_orders(_orders)
                        


if __name__ == "__main__":

    # Copy the directory of the param .yaml file and paste it below \
    param_dir = ""

    # Load initial configuration \
    with open(param_dir, "r") as f:
        config = yaml.safe_load(f)

    # Global parameters \
    tick_size = config['tick_size']
    lot_size = config['lot_size']
    account_size = config['account_size']
    quote_offset = config['quote_offset']
    size_offset = config['size_offset']
    target_spread = config['target_spread']
    volatility_offset = config['volatility_offset']
    minimum_order_size = config['minimum_order_size']
    maximum_order_size = config['maximum_order_size']
    inventory_extreme = config['inventory_extreme']
    inventory_neutral = config['inventory_neutral']

    # Global variables \
    inventory_delta = 0.0
    volatility_value = 1.0
    
    _run = asyncio.run(main('USDCUSDT'))





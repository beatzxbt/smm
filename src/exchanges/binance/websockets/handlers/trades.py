
import numpy as np
from src.sharedstate import SharedState



class BinanceTradesInit:


    def __init__(self, sharedstate: SharedState, recv) -> None:
        self.ss = sharedstate
        self.data = recv


    def process(self):

        for row in self.data:
            
            time = row['time']
            price = row['price']
            qty = row['qty']

            if row['isBuyerMaker']:
                side = 1
                
            else:
                side = 0

            new_trade = np.array([[time, side, price, qty]], dtype=float)

            self.ss.binance_trades.append(new_trade)



class BinanceTradesHandler:


    def __init__(self, sharedstate: SharedState, recv) -> None:
        self.ss = sharedstate
        self.data = recv['data']

    
    def process(self):

        time = self.data['T']
        price = self.data['p']
        qty = self.data['q']

        if self.data['m']:
            side = 1

        else:
            side = 0

        # Update last price \
        self.ss.binance_last_price = float(price)

        # New trade \
        new_trade = np.array([[time, side, price, qty]], dtype=float)

        # Append to array, ring buffer handles maxlen and overwrite \
        self.ss.binance_trades.append(new_trade)
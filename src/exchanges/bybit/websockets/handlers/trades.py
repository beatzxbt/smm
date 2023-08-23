
import numpy as np
from src.sharedstate import SharedState


class BybitTradesInit:


    def __init__(self, sharedstate: SharedState, data) -> None:
        self.ss = sharedstate
        self.data = data['result']['list']

    
    def process(self):

        for row in self.data:

            time = row['time']
            price = row['price']
            qty = row['size']

            if row['side'] == 'Buy':
                side = 0
                
            else:
                side = 1

            new_trade = np.array([[time, side, price, qty]], dtype=float)

            self.ss.bybit_trades.append(new_trade)



class BybitTradesHandler:


    def __init__(self, sharedstate: SharedState, data) -> None:
        self.ss = sharedstate
        self.data = data[0]

    
    def process(self):

        time = self.data['T']
        price = self.data['p']
        qty = self.data['v']

        if self.data['S'] == 'Buy':
            side = 0

        else:
            side = 1

        # New trade \
        new_trade = np.array([[time, side, price, qty]], dtype=float)

        # Append to array, ring buffer handles maxlen and overwrite \
        self.ss.bybit_trades.append(new_trade)
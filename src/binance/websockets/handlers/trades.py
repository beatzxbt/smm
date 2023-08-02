import json
import numpy as np


class BinanceTradesHandler:


    def __init__(self, sharedstate, recv: json) -> None:
        self.ss = sharedstate
        self.data = recv['data']

    
    def process(self):

        time = float(self.data['T'])
        price = float(self.data['p'])
        qty = float(self.data['q'])

        if self.data['s'] == 'Buy':
            side = 0.

        else:
            side = 1.

        # Update last price \
        self.ss.binance_last_price = price

        indv_trade = np.array([time, side, price, qty])
        self.ss.binance_trades.append(indv_trade)

        # Limit list size to 1000 trades \
        if len(self.ss.binance_trades) > 1000:
            self.ss.binance_trades.pop(0)
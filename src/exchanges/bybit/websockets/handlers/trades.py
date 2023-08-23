import json
import numpy as np



class BybitTradesHandler:


    def __init__(self, sharedstate, data: json) -> None:
        self.ss = sharedstate
        self.data = data

    
    def process(self):

        for trade in self.data:
            
            time = float(trade['T'])
            price = float(trade['p'])
            qty = float(trade['v'])

            if trade['S'] == 'Buy':
                side = float(0)

            else:
                side = float(1)

            indv_trade = np.array([time, side, price, qty])
            self.ss.bybit_trades.append(indv_trade)

            # Limit list size to 1000 trades \
            if len(self.ss.bybit_trades) > 1000:
                self.ss.bybit_trades.pop(0)

import numpy as np
from src.sharedstate import SharedState



class BinanceTradesHandler:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    def _init(self, data: dict):

        for row in data:
            time = row["time"]
            price = row["price"]
            qty = row["qty"]
            side = 1 if row["isBuyerMaker"] else 0
                
            new_trade = np.array([[time, side, price, qty]], dtype=float)
            self.ss.binance_trades.append(new_trade)


    def process(self, recv: dict):
        data = recv["data"]
        
        time = data["T"]
        price = data["p"]
        qty = data["q"]
        side = 1 if data["m"] else 0

        # Update last price
        self.ss.binance_last_price = float(price)

        # New trade
        new_trade = np.array([[time, side, price, qty]], dtype=float)

        # Append to array, ring buffer handles maxlen and overwrite
        self.ss.binance_trades.append(new_trade)
        
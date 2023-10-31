
import numpy as np
from frameworks.sharedstate.market import MarketDataSharedState



class BinanceTradesHandler:


    def __init__(self, mdss: MarketDataSharedState) -> None:
        self.mdss = mdss


    def initialize(self, data: dict) -> None:
        for row in data:
            time = row["time"]
            price = row["price"]
            qty = row["qty"]
            side = 1 if row["isBuyerMaker"] else 0
                
            new_trade = np.array([[time, side, price, qty]], dtype=float)
            self.mdss.binance_trades["trades"].append(new_trade)


    def update(self, recv: dict) -> None:
        time = recv["data"]["T"]
        price = recv["data"]["p"]
        qty = recv["data"]["q"]
        side = 1 if recv["data"]["m"] else 0

        new_trade = np.array([[time, side, price, qty]], dtype=float)
        self.mdss.binance_trades["trades"].append(new_trade)
        self.mdss.binance_trades["last_price"] = float(price)
        
import numpy as np
from numpy.typing import NDArray
from typing import Tuple, Dict, Union

from frameworks.tools.numba import nblinspace
from frameworks.tools.mids import mid
from smm.sharedstate import SmmSharedState


class BasicQuoteGenerator:
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
        self.params = self.ss.parameters
        
        self.tick_size = self.ss.misc["tick_size"]
        self.lot_size = self.ss.misc["lot_size"]

    @property
    def mid(self) -> float:
        return mid(self.ss.orderbook)
    
    def _bps_to_decimal_(self, bps: float) -> float:
        return bps / 10000
    
    def _spread_to_decimal_(self, bps: float) -> float:
        new_price = self.mid + (self.mid * self._bps_to_decimal_(bps))
        return new_price

    def corrected_skew(self, skew: float) -> float:
        """
        Calculate the set of features and return process its values to produce a bid & ask
        skew value corrected for current inventory
        """
        self.delta = self.ss.current_position / self.params["max_position"]
        corrective_amount = self.delta ** 2

        # Correct for current inventory
        skew += corrective_amount if self.delta > 0 else -corrective_amount

        return skew

    def corrected_spread(self, ideal_spread: float) -> float:
        if ideal_spread < self.params["minimum_spread"]:
            return self.params["minimum_spread"] / 10000
        
    

    def generate_quotes(self, skew: float, spread: float) -> Tuple[NDArray, NDArray]:
        orders = []

        # Exceeding max positive delta
        if self.delta > 1:
            num_orders = self.params["num_orders"]//2
            best_bid = self.ss.orderbook.bba[0, 0]
            worst_bid = best_bid - (best_bid * spread * num_orders)
            price_range = nblinspace(best_bid, worst_bid, num_orders)
            size_range = nblinspace(self.ss.current_position/5, self.ss.current_position/3, num_orders)
            
            for price, size in zip(price_range, size_range):
                orders.append([0, 0, price, size])

            return orders
        
        # Exceeding max negative delta
        elif self.delta < 1:
            num_orders = self.params["num_orders"]//2
            best_ask = self.ss.orderbook.bba[1, 0]
            worst_ask = best_ask + (best_ask * spread * num_orders)
            price_range = nblinspace(best_ask, worst_ask, num_orders)
            size_range = nblinspace(self.ss.current_position/5, self.ss.current_position/3, num_orders)
            
            for price, size in zip(price_range, size_range):
                orders.append([0, 1, price, size])

            return orders
        
        # Positive skew within bounds
        elif skew >= 0:
            # NOTE: The spread multiplers can be adjusted, and help to control fillrate
            best_bid = best_ask - (spread * 0.33)
            best_ask = best_bid + (spread * 0.67) 

            worst_bid = best_bid - (spread)
            worst_ask = best_ask + ()
            bid_price_range = nblinspace(best_bid, bid_lower, num_bids) 
            ask_price_range = nblinspace(best_ask, ask_upper, num_asks) 

            return bid_prices, ask_prices

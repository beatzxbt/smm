import numpy as np
from typing import List, Tuple

from frameworks.tools.numba import nblinspace
from smm.sharedstate import SmmSharedState
from smm.quote_generators.base import QuoteGenerator


class PlainQuoteGenerator(QuoteGenerator):
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
        super().__init__(self.ss)

        self.aggressiveness = self.ss.parameters["aggressiveness"]

    def corrected_skew(self, skew: float) -> float:
        """
        Calculate the set of features and return process its values to produce a bid & ask
        skew value corrected for current inventory
        """
        corrective_amount = self.inventory_delta ** 2.0
        skew += corrective_amount if self.inventory_delta < 0.0 else -corrective_amount
        return skew

    def corrected_spread(self, spread: float) -> float:
        if spread < self.params["minimum_spread"]:
            return self.params["minimum_spread"] / 10000
    
    def generate_prices(self, skew: float, spread: float) -> List[Tuple]:
        if skew > 0.0:
            best_bid = self.mid - (spread * (1.0 - self.aggressiveness))
            best_ask = self.live_best_bid[0] - bid_spread

        elif skew <= 0.0:
            bid_spread = spread * self.aggressiveness
            best_bid = self.mid - bid_spread

    def generate_sizes(self, skew: float) -> List[Tuple]:
        pass

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

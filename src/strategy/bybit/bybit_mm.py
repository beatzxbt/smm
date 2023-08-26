import numpy as np

from src.utils.rounding import round_step_size
from src.utils.jit_funcs import linspace, nsqrt, nabs

from src.strategy.features.momentum import trend_feature
from src.strategy.features.mark_spread import mark_price_spread

from src.sharedstate import SharedState


class CalculateFeatures:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    def momentum_klines(self):
        klines = self.ss.bybit_klines

        return trend_feature(klines, self.depths)


    def bybit_mark_spread(self):
        mark_price = self.ss.bybit_mark_price
        wmid = self.ss.bybit_weighted_mid_price

        return mark_price_spread(mark_price, wmid)


    def generate_skew(self):
        
        # Weights for momentum features (total, makes up 50% of value) \
        momentum_weight = 1.00 * 0.5

        # Weights for spread features (total, makes up 50% of value) \
        mark_spread_weight = 1.00 * 0.5

        # Generate all feature values \
        momentum = self.momentum_klines() * momentum_weight
        mark_spread = self.bybit_mark_spread() * mark_spread_weight

        skew = momentum + mark_spread

        return skew



class MarketMaker:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.max_orders = self.ss.num_orders


    def skew(self) -> float:
        """
        Generates bid/ask skew 

        _______________________________________________________________

        -> If inventory is positive (longs) or negative (shorts) but within bounds, skew is based on features 

        -> However if its are outside bounds, it skews the opposite side to help reduce inventory
        """

        skew = CalculateFeatures(self.ss).generate_skew()
        inventory_delta = self.ss.inventory_delta
        inventory_extreme = self.ss.inventory_extreme

        # Calculate skew using conditional vectorization \
        bid_skew = np.where(skew >= 0, np.clip(skew, 0, 1), 0)
        ask_skew = np.where(skew < 0, np.clip(skew, -1, 0), 0)

        # Neutralize inventory using conditional assignment \
        bid_skew[inventory_delta < 0] += inventory_delta
        ask_skew[inventory_delta > 0] -= inventory_delta

        # Handle extreme inventory cases using conditional assignment \
        bid_skew[inventory_delta < -inventory_extreme] = 1
        ask_skew[inventory_delta > inventory_extreme] = 1

        self.bid_skew = nabs(float(bid_skew))
        self.ask_skew = nabs(float(ask_skew))

        return bid_skew, ask_skew
        

    def quotes_price_range(self) -> np.array:
        """
        Generates bid/ask prices

        _______________________________________________________________

        DESCRIPTION NEEDS TO BE REDONE

        -> Volatility (range of quotes) is split into half (bid/ask) \n
        -> Upper limits are defined by the skew values (reduces the upper quote distance from base) \n
        -> A linear range from the mark price to the upper limit is generated 
        """
        
        best_bid_price = self.ss.bybit_bba[0][0]
        best_ask_price = self.ss.bybit_bba[1][0]
        base_range = self.ss.volatility_value/2

        # If inventory is too high, pull quotes from one side entirely \
        if self.bid_skew >= 1:
            self.num_bids = self.max_orders
            self.num_asks = None

            bid_lower = best_bid_price - (self.ss.bybit_tick_size * self.num_bids)
            bid_prices = linspace(best_bid_price, bid_lower, self.num_bids)
            ask_prices = None

            return bid_prices, ask_prices
            
        elif self.ask_skew >= 1:
            self.num_bids = None
            self.num_asks = self.max_orders

            ask_upper = best_ask_price + (self.ss.bybit_tick_size * self.num_asks)
            ask_prices = linspace(best_ask_price, ask_upper, self.num_asks)
            bid_prices = None

            return bid_prices, ask_prices

        # If inventory is within bounds, then quote both sides as with calculated skew \
        if self.bid_skew >= self.ask_skew:
            best_bid_price = best_ask_price - self.ss.bybit_tick_size
            best_ask_price = best_bid_price + self.ss.target_spread

            bid_lower = best_bid_price - (base_range * (1 - self.bid_skew))
            ask_upper = best_ask_price + (base_range * (1 - self.ask_skew))
            
            self.num_bids = int((self.max_orders / 2) * (1 + self.bid_skew))
            self.num_asks = self.max_orders - self.num_bids

            bid_prices = linspace(best_bid_price, bid_lower, self.num_bids) 
            ask_prices = linspace(best_ask_price, ask_upper, self.num_asks) 

        elif self.bid_skew < self.ask_skew:
            best_ask_price = best_bid_price + self.ss.bybit_tick_size
            best_bid_price = best_ask_price - self.ss.target_spread

            bid_lower = best_bid_price - (base_range * (1 - self.bid_skew))
            ask_upper = best_ask_price + (base_range * (1 - self.ask_skew))
            
            self.num_asks = int(self.max_orders / 2 * (1 + self.ask_skew))
            self.num_bids = self.max_orders - self.num_asks

            bid_prices = linspace(best_bid_price, bid_lower, self.num_bids) 
            ask_prices = linspace(best_ask_price, ask_upper, self.num_asks) 

        return bid_prices, ask_prices


    def quotes_size_range(self) -> np.array:
        """
        Generates bid/ask sizes 

        _______________________________________________________________

        DESCRIPTION NEEDS TO BE REDONE

        -> Produce a linear range of values between minimum and maximum order size \n
        -> Upper limits are defined by the skew values (reduces the upper quote size) \n
        -> If skew is high, then pull quotes from one side and have fixed, heavy size on the other \n
        """

        # If inventory is too high, pull quotes from one side entirely \
        if self.bid_skew >= 1:
            bid_const = np.median([self.ss.minimum_order_size, self.ss.maximum_order_size/2])
            bid_quantities = np.array([bid_const] * self.num_bids)
            ask_quantities = None

            return bid_quantities, ask_quantities

        elif self.ask_skew >= 1:
            ask_const = np.median([self.ss.minimum_order_size, self.ss.maximum_order_size/2])
            ask_quantities = np.array([ask_const] * self.num_asks)
            bid_quantities = None

            return bid_quantities, ask_quantities

        # Heavier size near BBA, decrease size near edge for bids \
        if self.bid_skew >= self.ask_skew:
            bid_min = self.ss.minimum_order_size * (1 + nsqrt(self.bid_skew, 1))
            bid_upper = self.ss.maximum_order_size * (1 - self.bid_skew) 

            bid_quantities = linspace(bid_min, bid_upper, self.num_bids) 
            ask_quantities = linspace(self.ss.minimum_order_size, self.ss.maximum_order_size, self.num_asks) 

        # Heavier size near BBA, decrease size near edge for asks \
        elif self.bid_skew < self.ask_skew:
            ask_min = self.ss.minimum_order_size * (1 + nsqrt(self.ask_skew, 1))
            ask_upper = self.ss.maximum_order_size * (1 - self.ask_skew) 

            ask_quantities = linspace(ask_min, ask_upper, self.num_asks) 
            bid_quantities = linspace(self.ss.minimum_order_size, self.ss.maximum_order_size, self.num_bids) 

        return bid_quantities, ask_quantities


    def market_maker(self) -> list:
        """
        This function outputs a list that contains tuples | struct (side: str, price: str, qty: str)

        It tries to send orders in a way that is most efficient for fills: 
            -> First 4 orders are most important, and will be amended in realtime by the diff function

            -> Rest of the orders are more passive, and will be managed by batch cancel/submissions
        """

        def append_bids(orders: list, bid_prices, bid_quantities):

            for i in range(len(bid_prices)):
                bid_p = round_step_size(bid_prices[i], self.ss.bybit_tick_size)
                bid_q = round_step_size(bid_quantities[i], self.ss.bybit_lot_size)
                orders.append(['Buy', bid_p, bid_q])

        def append_asks(orders: list, ask_prices, ask_quantities):

            for i in range(len(ask_prices)):
                ask_p = round_step_size(ask_prices[i], self.ss.bybit_tick_size)
                ask_q = round_step_size(ask_quantities[i], self.ss.bybit_lot_size)
                orders.append(['Sell', ask_p, ask_q])

        # Generate skew, then prices & sizing \ 
        self.skew()
        bid_prices, ask_prices = self.quotes_price_range()
        bid_quantities, ask_quantities = self.quotes_size_range()

        orders = []

        # If inventory is extremely long, number of bids will be None \
        if self.num_bids is None:
            append_asks(orders, ask_prices, ask_quantities)   
        
        # If inventory is extremely short, number of asks will be None \
        elif self.num_asks is None:
            append_bids(orders, bid_prices, bid_quantities) 

        # If inventory is within bounds, send orders in specified way \
        else: 
            # Append the first two bids and asks, which will amend in realtime \
            append_bids(orders, bid_prices[:2], bid_quantities[:2]) 
            append_asks(orders, ask_prices[:2], ask_quantities[:2])  

            # The rest, which will move in batches \
            append_bids(orders, bid_prices[2:], bid_quantities[2:]) 
            append_asks(orders, ask_prices[2:], ask_quantities[2:])  

        return orders
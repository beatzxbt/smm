import numpy as np

from src.utils.rounding import round_step_size
from src.utils.jit_funcs import linspace



class MarketMaker:


    def __init__(self, sharedstate) -> None:

        self.ss = sharedstate
        self.max_orders = int(self.ss.num_orders/2)

        self.bybit_mid = self.ss.bybit_mid_price
        self.binance_mid = self.ss.binance_mid_price


    def skew(self) -> float:
        """
        Generates bid/ask skew based on current inventory delta \n
        Also skews on difference between benchmark price and bybit price

        _______________________________________________________________

        -> If inventory is positive (longs) or negative (shorts) but within bounds, skew is normal \n
        -> However if its are outside bounds, it skews the opposite side to help reduce inventory
        """

        self.bid_skew = float()
        self.ask_skew = float()

        # Compare binance mid price with the bybit mid price \
        delta = np.log(self.binance_mid/self.bybit_mid) * 100

        if delta >= 0:
            self.bid_skew += np.clip(delta, 0, 1)

        if delta < 0: 
            self.ask_skew += np.clip(delta, -1, 0)

        # If inventory is at an extreme value, skew quotes hard for it \
        if self.ss.inventory_delta < -self.ss.inventory_extreme:
            self.bid_skew = 1
        
        if self.ss.inventory_delta > self.ss.inventory_extreme:
            self.ask_skew = 1

        return self.bid_skew, self.ask_skew
        

    def quotes_price_range(self) -> np.array:
        """
        Generates bid/ask prices

        _______________________________________________________________

        -> Volatility (range of quotes) is split into half (bid/ask) \n
        -> Checks are performed to adjust BBA inline with target spreads \n
        -> Upper limits are defined by the skew values (reduces the upper quote distance from base) \n
        -> A linear range from the mark price to the upper limit is generated 
        """

        best_bid_price = self.ss.bybit_bba[0][0]
        best_ask_price = self.ss.bybit_bba[1][0]
        base_range = self.ss.volatility_value/2

        # If quoted best bid is higher than actual best ask, then fallback to actual best ask - 1 tick \
        if self.binance_mid - self.ss.target_spread > best_ask_price:
            best_bid_price = best_ask_price - self.ss.bybit_tick_size

        else:
            best_bid_price = self.binance_mid - self.ss.target_spread

        # Same as above, but for asks \
        if self.binance_mid + self.ss.target_spread < best_bid_price:
            best_ask_price = best_bid_price + self.ss.bybit_tick_size    

        else:
            best_ask_price = self.binance_mid + self.ss.target_spread

        # If inventory is too high, pull quotes from one side entirely \
        if self.bid_skew >= 1:
            bid_lower = best_bid_price - (self.ss.bybit_tick_size * self.max_orders)
            bid_prices = linspace(best_bid_price, bid_lower, self.max_orders)

            return bid_prices, None

        elif self.ask_skew >= 1:
            ask_upper = best_ask_price + (self.ss.bybit_tick_size * self.max_orders)
            ask_prices = linspace(best_ask_price, ask_upper, self.max_orders)

            return None, ask_prices

        # If inventory is within bounds, then quote both sides as usual \
        else:
            bid_lower = best_bid_price - (base_range * (1 - self.bid_skew))
            ask_upper = best_ask_price + (base_range * (1 - self.ask_skew))
            
            bid_prices = linspace(best_bid_price, bid_lower, self.max_orders) + self.ss.quote_offset
            ask_prices = linspace(best_ask_price, ask_upper, self.max_orders) + self.ss.quote_offset

            return bid_prices, ask_prices


    def quotes_size_range(self) -> np.array:
        """
        Generates bid/ask sizes 

        _______________________________________________________________

        -> Produce a linear range of values between minimum and maximum order size \n
        -> Upper limits are defined by the skew values (reduces the upper quote size) \n
        -> If skew is high, then pull quotes from one side and have fixed, heavy size on the other \n
        """

        # If inventory is too high, pull quotes from one side entirely \
        if self.bid_skew >= 1:
            bid_const = np.median([self.ss.minimum_order_size, self.ss.maximum_order_size])
            bid_quantities = np.array([bid_const] * self.max_orders)

            return bid_quantities, None

        elif self.ask_skew >= 1:
            ask_const = np.median([self.ss.minimum_order_size, self.ss.maximum_order_size])
            ask_quantities = np.array([ask_const] * self.max_orders)

            return None, ask_quantities

        # If inventory is not too extreme, then quote both sides as usual \
        else:
            # Reduce max size if skew exists \
            bid_upper = self.ss.maximum_order_size / (1 - self.ask_skew) 
            ask_upper = self.ss.maximum_order_size / (1 - self.bid_skew) 

            bid_quantities = linspace(self.ss.minimum_order_size, bid_upper, self.max_orders) + self.ss.size_offset
            ask_quantities = linspace(self.ss.minimum_order_size, ask_upper, self.max_orders) + self.ss.size_offset

            return bid_quantities, ask_quantities


    def market_maker(self) -> list:
        """
        This function outputs a list that contains tuples | struct (side: str, price: str, qty: str) \n
        """

        # Generate skew, then prices & sizing \
        skew = self.skew()
        bid_prices, ask_prices = self.quotes_price_range()
        bid_quantities, ask_quantities = self.quotes_size_range()

        orders = []
        
        # If inventory is extremely long, bids will return None (check price func for more info) \
        if bid_prices is None:

            for i in range(self.max_orders):

                # Round everything at the end to save a few micros \
                ask_p = round_step_size(ask_prices[i], self.ss.bybit_tick_size)
                ask_q = round_step_size(ask_quantities[i], self.ss.bybit_lot_size)

                orders.append(['Sell', ask_p, ask_q])   
        
        # If inventory is extremely short, asks will return None (check price func for more info) \
        elif ask_prices is None:

            for i in range(self.max_orders):

                # Round everything at the end to save a few micros \
                bid_p = round_step_size(bid_prices[i], self.ss.bybit_tick_size)
                bid_q = round_step_size(bid_quantities[i], self.ss.bybit_lot_size)

                orders.append(['Buy', bid_p, bid_q])

        # If inventory is within bounds, send orders as usual on both sides \
        else: 
            for i in range(self.max_orders):

                # Round everything at the end to save a few micros \
                bid_p = round_step_size(bid_prices[i], self.ss.bybit_tick_size)
                bid_q = round_step_size(bid_quantities[i], self.ss.bybit_lot_size)
                ask_p = round_step_size(ask_prices[i], self.ss.bybit_tick_size)
                ask_q = round_step_size(ask_quantities[i], self.ss.bybit_lot_size)

                # Append orders alternating between bid/ask, away from BBA for ideal submission \
                orders.append(['Buy', bid_p, bid_q])
                orders.append(['Sell', ask_p, ask_q])   

        return orders     
        

import json
import numpy as np
from src.utils.rounding import round_step_size
from src.utils.jit_funcs import linspace


class Inventory:
    

    def __init__(self, position_feed_data: json) -> None:
        self.data = position_feed_data


    def calculate_delta(self, account_size: float) -> float:
        """
        Calculates the current position delta relative to account size
        """

        if self.data is None:
            pass

        else:
            side = str(self.data['side'])

            if side == '':
                inventory_delta = 0.0

            else:
                leverage = float(self.data['leverage'])
                position_size = float(self.data['positionValue'])
                maximum_position_size = (account_size/2) * leverage

                if side == 'Sell':
                    inventory_delta = -position_size/maximum_position_size

                elif side == 'Buy':
                    inventory_delta = position_size/maximum_position_size

            return inventory_delta



class Strategy:


    def __init__(self, tick_size: float, lot_size: float, num_orders: int, target_spread: float, 
                 minimum_order_size: float, maximum_order_size: float, quote_offset: float, \
                 size_offset: float) -> None:
        
        self.tick_size = float(tick_size)
        self.lot_size = float(lot_size)
        self.max_orders = int(num_orders)  
        self.target_spread = float(target_spread)
        self.quote_offset = float(quote_offset)
        self.size_offset = float(size_offset)
        self.minimum_order_size = float(minimum_order_size)
        self.maximum_order_size = float(maximum_order_size)
        

    def skew(self, inventory_delta: float, inventory_extreme: float) -> float:
        """
        Generates bid/ask skew based on current inventory delta 

        _______________________________________________________________

        -> If inventory is positive (longs) or negative (shorts) but within bounds, skew is 0 \n
        -> However if its are outside bounds, it skews the opposite side to help reduce inventory
        """

        bid_skew = 0.
        ask_skew = 0.

        if inventory_delta < -inventory_extreme:
            bid_skew += np.abs(inventory_delta) 
        
        elif inventory_delta > inventory_extreme:
            ask_skew += inventory_delta 

        return bid_skew, ask_skew
        

    def quotes_price_range(self, mark_price: float, volatility: float, bid_skew: float, \
                           ask_skew: float, bba: tuple) -> np.array:
        """
        Generates bid/ask prices

        _______________________________________________________________

        -> Volatility (range of quotes) is split into half (bid/ask) \n
        -> Checks are performed to adjust BBA inline with target spreads \n
        -> Upper limits are defined by the skew values (reduces the upper quote distance from base) \n
        -> A linear range from the mark price to the upper limit is generated 
        """

        best_bid = bba[0]
        best_ask = bba[1]
        base_range = volatility/2
        max_orders = int(self.max_orders/2)

        # If quoted best bid is higher than actual best ask, then fallback to actual best ask - 1 tick \
        if mark_price - self.target_spread > best_ask:
            best_bid = best_ask - self.tick_size

        else:
            best_bid = mark_price - self.target_spread

        # Same as above, but for asks \
        if mark_price + self.target_spread < best_bid:
            best_ask = best_bid + self.tick_size    

        else:
            best_ask = mark_price + self.target_spread

        # If inventory is too high, pull quotes from one side entirely \
        # If inventory is not too extreme, then quote both sides as usual \
        if bid_skew > 0.5:
            bid_lower = best_bid - (base_range * (1-bid_skew))
            bid_prices = linspace(best_bid, bid_lower, max_orders) + self.quote_offset

            return bid_prices, None

        elif ask_skew > 0.5:
            ask_upper = best_ask + (base_range * (1-ask_skew))
            ask_prices = linspace(best_ask, ask_upper, max_orders) + self.quote_offset

            return None, ask_prices

        else:
            bid_lower = best_bid - (base_range * (1-bid_skew))
            ask_upper = best_ask + (base_range * (1-ask_skew))

            bid_prices = linspace(best_bid, bid_lower, max_orders) + self.quote_offset
            ask_prices = linspace(best_ask, ask_upper, max_orders) + self.quote_offset

            return bid_prices, ask_prices


    def quotes_size_range(self, bid_skew: float, ask_skew: float) -> np.array:
        """
        Generates bid/ask sizes 

        _______________________________________________________________

        -> Produce a linear range of values between minimum and maximum order size \n
        -> Upper limits are defined by the skew values (reduces the upper quote size) \n
        -> If skew is high, then pull quotes from one side and have fixed, heavy size on the other \n
        """

        max_orders = int(self.max_orders/2)

        # If inventory is too high, pull quotes from one side entirely \
        # If inventory is not too extreme, then quote both sides as usual \
        if bid_skew > 0.5:
            bid_const = np.median([self.minimum_order_size, self.maximum_order_size])
            bid_quantities = np.array([bid_const] * max_orders) + self.quote_offset

            return bid_quantities, None

        elif ask_skew > 0.5:
            ask_const = np.median([self.minimum_order_size, self.maximum_order_size])
            ask_quantities = np.array([ask_const] * max_orders) + self.quote_offset

            return None, ask_quantities

        else:
            # Reduce max size if skew exists, otherwise fixed size
            bid_upper = self.maximum_order_size / (1 - ask_skew) 
            ask_upper = self.maximum_order_size / (1 - bid_skew) 

            bid_quantities = linspace(self.minimum_order_size, bid_upper, max_orders) + self.size_offset
            ask_quantities = linspace(self.minimum_order_size, ask_upper, max_orders) + self.size_offset

            return bid_quantities, ask_quantities


    def market_maker(self, mark_price: float, volatility: float, bba: tuple, \
                     inventory_delta: float, inventory_extreme: float, ) -> list:
        """
        {mark_price}: central value, which quotes will be placed around \n
        {volatility}: directly effects range & size of quotes \n
        {inventory_delta}: normalized value between -1 and 1 of current inventory \n

        This function outputs a list that contains tuples | struct (side: str, price: str, qty: str) \n
        """

        bid_skew, ask_skew = self.skew(inventory_delta, inventory_extreme)
        bid_prices, ask_prices = self.quotes_price_range(mark_price, volatility, bid_skew, ask_skew, bba)
        bid_quantities, ask_quantities = self.quotes_size_range(bid_skew, ask_skew)

        orders = []
        max_orders = int(self.max_orders/2)
        
        # If inventory is extremely long, bids will return None (check price func for more info) \
        if bid_prices is None:

            for i in range(max_orders):
                # Round everything at the end to save a few micros \
                ask_p = round_step_size(ask_prices[i], self.tick_size)
                ask_q = round_step_size(ask_quantities[i], self.lot_size)

                orders.append(['Sell', str(ask_p), str(ask_q)])   
        
        # If inventory is extremely short, asks will return None (check price func for more info) \
        elif ask_prices is None:

            for i in range(max_orders):
                # Round everything at the end to save a few micros \
                bid_p = round_step_size(bid_prices[i], self.tick_size)
                bid_q = round_step_size(bid_quantities[i], self.lot_size)

                orders.append(['Buy', str(bid_p), str(bid_q)])

        # If inventory is within bounds, send orders as usual on both sides \
        else: 
            for i in range(max_orders):
                # Round everything at the end to save a few micros \
                bid_p = round_step_size(bid_prices[i], self.tick_size)
                bid_q = round_step_size(bid_quantities[i], self.lot_size)
                ask_p = round_step_size(ask_prices[i], self.tick_size)
                ask_q = round_step_size(ask_quantities[i], self.lot_size)

                # Append orders alternating between bid/ask, away from BBA for ideal submission \
                orders.append(['Buy', str(bid_p), str(bid_q)])
                orders.append(['Sell', str(ask_p), str(ask_q)])   

        return orders     
        



        


    
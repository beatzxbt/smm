
import numpy as np

from src.utils.rounding import round_step_size
from src.utils.jit_funcs import nlinspace, nsqrt, nabs, npower
from src.strategy.features.momentum import trend_feature, trend_feature_v2
from src.strategy.features.mark_spread import mark_price_spread
from src.strategy.features.bba_imbalance import bba_imbalance

from src.sharedstate import SharedState


class CalculateFeatures:
    """
    Some features are disabled for Bybit-only streams    
    """

    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate

        self.depths = np.array([200, 100, 50, 25, 10])
        self.klines = self.ss.bybit_klines._unwrap()
        self.bybit_trades = self.ss.bybit_trades._unwrap()
        self.binance_trades = self.ss.binance_trades._unwrap()


    def momentum_klines(self):
        return trend_feature(
            klines=self.klines, 
            lengths=self.depths
        )


    def bybit_mark_wmid_spread(self):
        return mark_price_spread(
            mark_price=self.ss.bybit_mark_price, 
            wmid=self.ss.bybit_weighted_mid_price
        )


    def binance_bybit_wmid_spread(self):
        return mark_price_spread(
            mark_price=self.ss.binance_weighted_mid_price, 
            wmid=self.ss.bybit_weighted_mid_price
        )

    
    def bybit_bba_imbalance(self):
        return bba_imbalance(
            bid=self.ss.bybit_bba[0][1], 
            ask=self.ss.bybit_bba[1][1]
        )

    
    def binance_bba_imbalance(self):
        return bba_imbalance(
            bid=self.ss.binance_bba[0][1], 
            ask=self.ss.binance_bba[1][1]
        )


    def generate_skew(self):
        
        total_skew = 0

        if self.ss.primary_data_feed == "BINANCE":
            momentum_weight = 0.4
            bybit_spread_weight = 0.2
            binance_spread_weight = 0.2
            bybit_bba_imb_weight = 0.1
            binance_bba_imb_weight = 0.1

            # Generate all feature values
            total_skew += self.momentum_klines() * momentum_weight
            total_skew += self.bybit_mark_wmid_spread() * bybit_spread_weight
            total_skew += self.binance_bybit_wmid_spread() * binance_spread_weight
            total_skew += self.bybit_bba_imbalance() * bybit_bba_imb_weight
            total_skew += self.binance_bba_imbalance() * binance_bba_imb_weight

        else:
            momentum_weight = 0.5
            bybit_spread_weight = 0.3
            bybit_bba_imb_weight = 0.2

            # Generate all feature values
            total_skew += self.momentum_klines() * momentum_weight
            total_skew += self.bybit_mark_wmid_spread() * bybit_spread_weight
            total_skew += self.bybit_bba_imbalance() * bybit_bba_imb_weight

        return total_skew



class MarketMaker:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate
        self.calculate_features = CalculateFeatures(self.ss)
        self.max_orders = self.ss.num_orders
        self.tick_size = self.ss.bybit_tick_size
        self.lot_size = self.ss.bybit_lot_size

        self.spread = self._adjspread()


    def _skew(self) -> tuple[float, float]:
        """
        Generates bid & ask skew 

        _______________________________________________________________

        -> If inventory within bounds, skew = feature values

        -> Otherwise, quotes skewed to reduce inventory
        """

        skew = self.calculate_features.generate_skew()
        skew = np.round(skew, 1)

        # Calculate skew using conditional vectorization
        bid_skew = np.where(skew >= 0, np.clip(skew, 0, 1), 0)
        ask_skew = np.where(skew < 0, np.clip(skew, -1, 0), 0)

        # Neutralize inventory using conditional assignment
        bid_skew[self.ss.inventory_delta < 0] += self.ss.inventory_delta
        ask_skew[self.ss.inventory_delta > 0] -= self.ss.inventory_delta

        # Handle extreme inventory cases using conditional assignment
        bid_skew[self.ss.inventory_delta < -self.ss.inventory_extreme] = 1
        ask_skew[self.ss.inventory_delta > self.ss.inventory_extreme] = 1

        # Final skews
        bid_skew = nabs(float(bid_skew))
        ask_skew = nabs(float(ask_skew))

        return bid_skew, ask_skew


    def _adjspread(self) -> float:
        """
        Increases the base spread in volatile moments
        """
        multiplier = (self.ss.volatility_value * 100) / self.ss.bybit_mid_price
        multiplier = np.clip(multiplier, 1, 10)

        return self.ss.base_spread * multiplier


    def _num_orders(self, bid_skew, ask_skew) -> tuple[float, float]:
        """
        Returns the number of bids & asks to generate
        """

        if bid_skew > ask_skew:
            num_bids = int((self.max_orders / 2) * (1 + npower(bid_skew, 1.5)))
            num_asks = self.max_orders - num_bids

        else:
            num_asks = int((self.max_orders / 2) * (1 + npower(ask_skew, 1.5)))
            num_bids = self.max_orders - num_asks

        # Extreme inventory kills quotes on one side
        num_bids = None if ask_skew >= 1 else num_bids
        num_asks = None if bid_skew >= 1 else num_asks

        return num_bids, num_asks


    def _prices(self, bid_skew, ask_skew, num_bids, num_asks) -> tuple[np.ndarray, np.ndarray]:
        """
        Generates bid & ask prices

        _______________________________________________________________

        -> Volatility (range of quotes) is split into half (bid/ask)
        -> Upper limits are defined by the skew values (reduces the upper quote distance from base)
        -> A linear range from the mark price to the upper limit is generated 
        """
        
        best_bid = self.ss.bybit_bba[0][0]
        best_ask = self.ss.bybit_bba[1][0]

        # If bid skew is too high, dont quote asks
        if bid_skew >= 1:
            bid_lower = best_bid - (self.tick_size * num_bids)
            bid_prices = nlinspace(best_bid, bid_lower, num_bids)

            return bid_prices, None
        
        # If ask skew is too high, dont quote bids
        elif ask_skew >= 1:
            ask_upper = best_ask + (self.tick_size * num_asks)
            ask_prices = nlinspace(best_ask, ask_upper, num_asks)

            return None, ask_prices

        # If skew is normal, quote both sides
        elif bid_skew >= ask_skew:
            best_bid = best_ask - self.tick_size
            best_ask = best_bid + self.spread            

        elif bid_skew < ask_skew:
            best_ask = best_bid + self.tick_size
            best_bid = best_ask - self.spread
        
        # Prices for both sides
        base_range = self.ss.volatility_value/2
        bid_lower = best_bid - (base_range * (1 - bid_skew))
        ask_upper = best_ask + (base_range * (1 - ask_skew))
            
        bid_prices = nlinspace(best_bid, bid_lower, num_bids) 
        ask_prices = nlinspace(best_ask, ask_upper, num_asks) 

        return bid_prices, ask_prices


    def _sizes(self, bid_skew, ask_skew, num_bids, num_asks) -> tuple[np.ndarray, np.ndarray]:
        """
        Generates bid/ask sizes 

        _______________________________________________________________


        -> Produce a linear range of values between minimum and maximum order sizen
        -> Upper limits are defined by the skew values (reduces the upper quote size)n
        -> If skew is high, then pull quotes from one side and have fixed, heavy size on the othern
        """

        # If bid skew is too high, dont quote asks
        if bid_skew >= 1:
            bid_sizes = np.full(
                shape=num_bids, 
                fill_value = np.median([self.ss.min_order_size, self.ss.max_order_size / 2])
            )

            return bid_sizes, None
        
        # If ask skew is too high, dont quote bids
        elif ask_skew >= 1:
            ask_sizes = np.full(
                shape=num_asks, 
                fill_value = np.median([self.ss.min_order_size, self.ss.max_order_size / 2])
            )

            return None, ask_sizes

        # Increased size near best bid, decreased size near worst bid
        bid_min = self.ss.min_order_size * (1 + nsqrt(bid_skew, 1))
        bid_upper = self.ss.max_order_size * (1 - bid_skew)

        # Increased size near best ask, decreased size near worst ask
        ask_min = self.ss.min_order_size * (1 + nsqrt(ask_skew, 1))
        ask_upper = self.ss.max_order_size * (1 - ask_skew)

        bid_sizes = nlinspace(
            start=bid_min if bid_skew >= ask_skew else self.ss.min_order_size, 
            end=bid_upper, 
            n=num_bids
        )

        ask_sizes = nlinspace(
            start=ask_min if ask_skew >= bid_skew else self.ss.min_order_size, 
            end=ask_upper, 
            n=num_asks
        )

        return bid_sizes, ask_sizes


    def generate_quotes(self) -> list[tuple[str, float, float]]:
        """
        Output: List of tuples | struct (side: str, price: str, qty: str)
        """

        def _append(orders, side, prices, sizes):
            for i in range(len(prices)):
                price = round_step_size(prices[i], self.tick_size)
                size = round_step_size(sizes[i], self.lot_size)
                orders.append([side, price, size])

        bid_skew, ask_skew = self._skew()
        num_bids, num_asks = self._num_orders(bid_skew, ask_skew)
        bid_prices, ask_prices = self._prices(bid_skew, ask_skew, num_bids, num_asks)
        bid_sizes, ask_sizes = self._sizes(bid_skew, ask_skew, num_bids, num_asks)

        orders = []

        # If inventory is extremely long, num_bids will be None
        if num_bids is not None:
            _append(orders, 'Buy', bid_prices, bid_sizes)   
        
        # If inventory is extremely short, num_asks will be None
        if num_asks is not None:
            _append(orders, 'Sell', ask_prices, ask_sizes)  

        return orders

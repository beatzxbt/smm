import numpy as np
from typing import Tuple, Dict, Union

from frameworks.tools.numba_funcs import nblinspace, nbround
from frameworks.sharedstate import SharedState
from smm.settings import SmmParameters

from frameworks.tools.mids import mid, wmid, vamp, weighted_vamp


class Features:
    """
    Configure your features here!
    """

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss

        self.settings = {
            "momentum_tick_bucket_size": 10,
            "momentum_ema_lengths": np.array([200, 100, 50, 25, 10]),
        }

        self.weights = {
            "wmid": 0.25,
            "vamp": 0.25,
            "wvamp": 0.25,
            "momentum": 0.25
        }

        self.cache = {
            "tick_candles": None
        }

        self.skew = 0
        
    def _wmid_(self, bba) -> float:
        return wmid(bba)

    def _vamp_(self, orderbook) -> float:
        return vamp(orderbook.asks, orderbook.bids)

    def _wvamp_(self, orderbook) -> float:
        return weighted_vamp(orderbook.asks, orderbook.bids)
    
    def _momentum_(self) -> float:
        return 

    def update(self):
        self.skew = 0
        self.skew += self._wmid_() * self.weights["wmid"]
        self.skew += self._vamp_() * self.weights["vamp"]
        self.skew += self._wvamp_() * self.weights["wvamp"]
        self.skew += self._momentum_() * self.weights["momentum"]


class BasicQuoteGenerator:

    def __init__(self, ss: SharedState, params: SmmParameters) -> None:
        self.ss = ss
        self.params = params
        self.logging = self.ss.logging

        self.features = Features(self.ss)

        self._verify_params_(self.params)
        
    def _verify_params_(self: Dict) -> Union[bool, Exception]:
        """
        Verify the presence of essential parameters in the strategy params for 
        this strategy, and throw an exception if incorrect/missing.

        Parameters
        ----------
        self : @self
            Uses self.params as the parameters dictionary

        Returns
        -------
        bool:
            True if verified, False otherwise
        """

        required_params = ["min_spread", "min_order_size", "max_order_size"]

        for rp in required_params:
            not_exists = self.params.get(rp) is None

            if not_exists:
                self.logging.critical(f"The parameter '{rp}' doesn't exist in the configuration file")
                raise ValueError


    def _skew_(self) -> Tuple[float, float]:
        """
        Calculate the set of features and return process its values to produce a bid & ask
        skew value corrected for current inventory

        Returns: 
            tuple[float, float]
        """

        # Calculate skew using conditional vectorization
        bid_skew = np.where(skew >= 0, np.clip(skew, 0, 1), 0)
        ask_skew = np.where(skew < 0, np.clip(skew, -1, 0), 0)

        # Neutralize inventory
        bid_skew[inventory < 0] += inventory
        ask_skew[inventory > 0] -= inventory

        # Final skews
        bid_skew = nabs(float(bid_skew))
        ask_skew = nabs(float(ask_skew))

        return bid_skew, ask_skew


    def _spread(
        self
    ) -> float:
        """
        Increases the base spread in volatile moments
        """

        multiplier = (self.ss.volatility_value * 100) / self.ss.bybit_mid_price
        multiplier = np.clip(multiplier, 1, 10)

        return self.ss.base_spread * multiplier


    def _num_orders(
        self, 
        bid_skew: float, 
        ask_skew: float
    ) -> tuple[float, float]:
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


    def _prices(
        self, 
        bid_skew: float, 
        ask_skew: float,
        num_bids: float, 
        num_asks: float
    ) -> tuple[np.ndarray, np.ndarray]:
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


    def _sizes(
        self, 
        bid_skew: float, 
        ask_skew: float, 
        num_bids: float, 
        num_asks: float
    ) -> tuple[np.ndarray, np.ndarray]:
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


    def generate_quotes(
        self
    ) -> list[tuple[str, float, float]]:
        """
        Final quote generator 
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

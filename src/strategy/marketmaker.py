import numpy as np
from numpy.typing import NDArray
from typing import List, Tuple
from src.utils.rounding import round_step
from src.utils.jit_funcs import nblinspace, nbgeomspace, nbround, nbabs, nbclip
from src.strategy.features.generate import Features
from src.sharedstate import SharedState


class MarketMaker:
    """
    Implements market making strategies including quote generation based on skew,
    spread adjustment for volatility, and order size calculations.

    Attributes
    ----------
    ss : SharedState
        Shared application state containing configuration and market data.
    features : Features
        A class instance for calculating market features like skew.
    tick_size : float
        The minimum price movement of an asset.
    lot_size : float
        The minimum quantity movement of an asset.
    spread : float
        The adjusted spread based on market volatility.

    Methods
    -------
    _skew_() -> Tuple[float, float]:
        Calculates bid and ask skew based on inventory and market conditions.
    _adjusted_spread_() -> float:
        Adjusts the base spread according to market volatility.
    _prices_(bid_skew: float, ask_skew: float) -> Tuple[np.ndarray, np.ndarray]:
        Generates bid and ask prices based on market conditions and skew.
    _sizes_(bid_skew: float, ask_skew: float) -> Tuple[np.ndarray, np.ndarray]:
        Calculates the sizes for bid and ask orders based on skew.
    generate_quotes() -> List[Tuple[str, float, float]]:
        Generates a list of quotes to be submitted to the exchange.
    """

    max_orders = 8

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.features = Features(self.ss)
        self.tick_size = self.ss.bybit_tick_size
        self.lot_size = self.ss.bybit_lot_size
        self.spread = self._adjusted_spread_()

    def _skew_(self) -> Tuple[float, float]:
        """
        Calculates the skew for bid and ask orders based on the current inventory level and generated skew value.

        Steps:
        1. Generate a base skew value from market features.
        2. Adjust the skew based on the current inventory level to encourage balancing.
        3. Limit skew adjustment to prevent extreme order placement if inventory is beyond predefined thresholds.
        
        Returns
        -------
        Tuple[float, float]
            The absolute values of bid and ask skew, ensuring they are positive.
        """
        skew = self.features.generate_skew()
        skew = nbround(skew, 2) # NOTE: Temporary, prevents heavy OMS use

        # Set the initial values
        bid_skew = nbclip(skew, 0, 1)
        ask_skew = nbclip(skew, -1, 0)  

        # Adjust for current inventory delta 
        bid_skew += self.ss.inventory_delta if self.ss.inventory_delta < 0 else 0
        ask_skew -= self.ss.inventory_delta if self.ss.inventory_delta > 0 else 0

        # Clip values if inventory reaches extreme levels
        bid_skew = bid_skew if self.ss.inventory_delta > -self.ss.inventory_extreme else 1
        ask_skew = ask_skew if self.ss.inventory_delta < self.ss.inventory_extreme else 1
        
        # Edge case where skew is extreme for no apparent reason (0 delta is rare here)
        if (bid_skew == 1 or ask_skew == 1) and (self.ss.inventory_delta == 0):
            return 0, 0
        
        return nbabs(bid_skew), nbabs(ask_skew)

    def _adjusted_spread_(self) -> float:
        """
        Adjusts the base spread of orders based on current market volatility.

        Steps:
        1. Calculate a multiplier based on the current volatility and mid price.
        2. Adjust the base spread by this multiplier, within a clipped range to prevent extreme spreads.

        Returns
        -------
        float
            The adjusted spread value.
        """
        multiplier = (self.ss.volatility_value * 100) / self.ss.bybit_mid
        return self.ss.base_spread * nbclip(multiplier, 1, 10)

    def _prices_(self, bid_skew: float, ask_skew: float) -> Tuple[NDArray, NDArray]:
        """
        Generates a list of bid and ask prices based on market conditions and skew.

        Steps:
        1. Determine base bid and ask prices from the current BBA.
        2. Adjust the prices based on the skew to generate a range for orders.
        3. Create linearly spaced prices within this range.

        Parameters
        ----------
        bid_skew : float
            The skew value for bid orders.
        ask_skew : float
            The skew value for ask orders.

        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            Arrays of bid and ask prices.
        """
        best_bid, best_ask = self.ss.bybit_bba[:, 0]

        # If inventory is too long, dont quote bids
        if bid_skew >= 1:
            bid_lower = best_bid - (self.spread * self.max_orders)
            bid_prices = nblinspace(best_bid, bid_lower, self.max_orders)
            return bid_prices, None
        
        # If inventory is too short, dont quote asks
        elif ask_skew >= 1:
            ask_upper = best_ask + (self.spread * self.max_orders)
            ask_prices = nblinspace(best_ask, ask_upper, self.max_orders)
            return None, ask_prices

        # If skew is normal, quote both sides
        elif bid_skew >= ask_skew:
            best_bid = best_ask - self.spread * 0.33
            best_ask = best_bid + self.spread * 0.67       

        elif bid_skew < ask_skew:
            best_ask = best_bid + self.spread * 0.33
            best_bid = best_ask - self.spread * 0.67 
        
        base_range = self.ss.volatility_value/2
        bid_lower = best_bid - (base_range * (1 - bid_skew))
        ask_upper = best_ask + (base_range * (1 - ask_skew))
            
        bid_prices = nbgeomspace(best_bid, bid_lower, self.max_orders/2) 
        ask_prices = nbgeomspace(best_ask, ask_upper, self.max_orders/2) 

        return bid_prices, ask_prices

    def _sizes_(self, bid_skew: float, ask_skew: float) -> Tuple[NDArray, NDArray]:
        """
        Calculates order sizes for bid and ask orders, adjusting based on skew and inventory levels.

        Steps:
        1. Set increased sizes for orders closer to the current price to entice trades that balance inventory.
        2. Decrease sizes for orders further from the current price to manage risk.

        Parameters
        ----------
        bid_skew : float
            The skew value for bid orders.
        ask_skew : float
            The skew value for ask orders.

        Returns
        -------
        Tuple[np.ndarray, np.ndarray]
            Arrays of sizes for bid and ask orders.
        """
        # If inventory is too long, dont quote bids
        if bid_skew >= 1:
            bid_sizes = np.full(
                shape=self.max_orders, 
                fill_value=np.median([self.ss.min_order_size, self.ss.max_order_size / 2])
            )
            return bid_sizes, None
        
        # If inventory is too short, dont quote asks
        elif ask_skew >= 1:
            ask_sizes = np.full(
                shape=self.max_orders, 
                fill_value=np.median([self.ss.min_order_size, self.ss.max_order_size / 2])
            )
            return None, ask_sizes

        # Increased size near best bid, decreased size near furthest bid
        bid_min = self.ss.min_order_size * (1 + bid_skew**0.5)
        bid_upper = self.ss.max_order_size * (1 - bid_skew)

        # Increased size near best ask, decreased size near furthest ask
        ask_min = self.ss.min_order_size * (1 + ask_skew**0.5)
        ask_upper = self.ss.max_order_size * (1 - ask_skew)

        bid_sizes = nbgeomspace(
            start=bid_min if bid_skew >= ask_skew else self.ss.min_order_size, 
            end=bid_upper, 
            n=self.max_orders/2
        )

        ask_sizes = nbgeomspace(
            start=ask_min if ask_skew >= bid_skew else self.ss.min_order_size, 
            end=ask_upper, 
            n=self.max_orders/2
        )

        return bid_sizes, ask_sizes

    def generate_quotes(self, debug=False) -> List[Tuple[str, float, float]]:
        """
        Generates a list of market making quotes to be placed on the exchange.

        Steps:
        1. Calculate skew values to determine the direction of inventory adjustment.
        3. Generate prices and sizes for both bid and ask orders.
        4. Aggregate and return the quotes for submission.

        Returns
        -------
        List[Tuple[str, float, float]]
            A list of quotes, where each quote is a tuple containing the side, price, and size.
        """
        bid_skew, ask_skew = self._skew_()
        bid_prices, ask_prices = self._prices_(bid_skew, ask_skew)
        bid_sizes, ask_sizes = self._sizes_(bid_skew, ask_skew)

        bids, asks = [], []

        if isinstance(bid_prices, np.ndarray):
            bids = [
                ["Buy", round_step(price, self.tick_size), round_step(size, self.lot_size)]
                for price, size in zip(bid_prices, bid_sizes)
            ]
        
        if isinstance(ask_prices, np.ndarray):
            asks = [
                ["Sell", round_step(price, self.tick_size), round_step(size, self.lot_size)]
                for price, size in zip(ask_prices, ask_sizes)
            ]

        if debug:
            print("-----------------------------")
            print(f"Skews: {bid_skew} |  {ask_skew}")
            print(f"Inventory: {self.ss.inventory_delta}")
            print(f"Bids: {bids}")
            print(f"Asks: {asks}")

        return bids + asks, self.spread
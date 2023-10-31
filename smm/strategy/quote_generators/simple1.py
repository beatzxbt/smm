
import numpy as np

from frameworks.tools.rounding import round_step_size
from frameworks.tools.numba_funcs import nlinspace, nsqrt, nabs, npower, nround
from frameworks.sharedstate.market import MarketDataSharedState
from frameworks.sharedstate.private import PrivateDataSharedState

from smm.settings import StrategyParameters
from smm.strategy.features.generate import CalculateFeatures


class SimpleQuoteGenerator:
    """
    Aims to maximise mean reverting nature of deep fills whilst
    capturing near-BBA spreads with basic inventory management 

    Explanation: https://twitter.com/BeatzXBT/status/1711348007688364263
    """

    def __init__(
        self, 
        mdss: MarketDataSharedState, 
        pdss: PrivateDataSharedState,
        strategy_params: StrategyParameters
    ) -> None:

        self.mdss = mdss
        self.pdss = pdss
        self.strategy = strategy_params

        # Ensure that all essential parameters for strategy as present
        self._verify_configuration(self.strategy)


    def _verify_configuration(
        self, 
        strategy_params: dict
    ) -> None | Exception:

        """
        Verify the presence of essential parameters in the strategy configuration.

        This function is an essential part of the strategy framework, ensuring that
        required configuration parameters are available for each strategy.

        Args:
            strategy_params (StrategyParameters): The instance containing strategy configuration

        Returns: 
            None if config is verified, otherwise raises Exception
        """

        params = ["min_order_size", "max_order_size"]

        for param in params:
            not_exists = strategy_params.get(param) is None

            if not_exists:
                raise ValueError(f"The parameter '{param}' doesn't exist in the configuration file.")


    def _skew(
        self
    ) -> tuple[float, float]:
        """
        Calculate the set of features and return process its values to produce a bid & ask
        skew value corrected for current inventory

        Returns: 
            tuple[float, float]: 
        """

        skew = CalculateFeatures(self.mdss, "recheck this area").generate_skew()

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
        bid_skew = nround(nabs(float(bid_skew)), 2)
        ask_skew = nround(nabs(float(ask_skew)), 2)

        return bid_skew, ask_skew


    def _inner_spread(
        self
    ) -> float:
        """
        Calculates the optimal base spread for BBA orders
        """

        maker_fees_num = (self.maker_fees * 2) / 10_000
        base_num = maker_fees_num * self.ss.bybit_mid_price

        vol_multiplier = (self.ss.volatility_value * 100) / self.ss.bybit_mid_price

        inner_spread = base_num * (1 if vol_multiplier < 1 else vol_multiplier)
        inner_spread_rounded = round_step_size(inner_spread, self.tick_size)

        return inner_spread_rounded


    def _inner_prices(
        self, 
        bid_skew: float, 
        ask_skew: float
    ) -> tuple[float, float]:
        """
        Generates the prices for BBA orders 
        """
        
        base_spread = self._inner_spread()
        inner_bid = self.best_bid if bid_skew > ask_skew else self.best_ask - base_spread
        inner_ask = self.best_ask if ask_skew > bid_skew else self.best_bid + base_spread

        return inner_bid, inner_ask
        

    def _inner_quantities(
        self, 
        bid_skew: float, 
        ask_skew: float
    ) -> tuple[float, float]:
        """
        Generates the quantities for BBA orders
        """

        target_inventory = bid_skew if bid_skew > ask_skew else -ask_skew
        target_inventory = self.asset_inventory.calculate_inventory_size(
            delta=target_inventory
        )

        diff = round_step_size(target_inventory - self.ss.inventory_size, self.lot_size)

        inner_bid = diff if diff >= 0 else self.lot_size
        inner_ask = diff if diff < 0 else self.lot_size

        return inner_bid, inner_ask


    def _generate_inner_orders(
        self, 
        inner_prices, 
        inner_quantities
        ) -> List:

        def _inner_append(orders, side: str, price: float, size: float):
            price = round_step_size(price, self.tick_size)
            size = round_step_size(size, self.lot_size)
            orders.append([side, price, size])

        inner_orders = []
        _inner_append(inner_orders, "Buy", inner_prices[0], inner_quantities[0])
        _inner_append(inner_orders, "Sell", inner_prices[1], inner_quantities[1])

        return inner_orders


    def _outer_spread(
        self
        ) -> float:
        """
        Calculates the optimal base spread for BBA orders
        """

        taker_fees_num = (self.taker_fees * 2) / 10_000
        base_num = taker_fees_num * self.ss.bybit_mid_price

        vol_multiplier = (self.ss.volatility_value * 100) / self.ss.bybit_mid_price

        base_spread = base_num * (1 if vol_multiplier < 1 else vol_multiplier)
        base_spread_rounded = round_step_size(base_spread, self.tick_size)

        return base_spread_rounded


    def _outer_prices(
        self,
        ) -> Tuple:
        """
        ccc
        """

        outer_min_spread = np.max([self._inner_spread()*2, self._outer_spread()]) 
        close_outer_bid = self.best_bid - outer_min_spread
        close_outer_ask = self.best_ask + outer_min_spread
 
        far_outer_bid = close_outer_bid - self._outer_spread() * 4 
        far_outer_ask = close_outer_ask + self._outer_spread() * 4 

        outer_bid_range = nlinspace(close_outer_bid, far_outer_bid, 4)
        outer_ask_range = nlinspace(close_outer_ask, far_outer_ask, 4)
        
        return outer_bid_range, outer_ask_range


    def _outer_quantities(
        self
        ) -> Tuple:
        """
        ccc
        """
        
        max_size = self.asset_inventory.calculate_inventory_size(
            delta=0.5, # No more than half the account should be filled in 1 go
        )

        all_qty = np.full(4, max_size/4)

        return all_qty, all_qty


    def _generate_outer_quotes(
        self,
        outer_prices, 
        outer_quantities
        ) -> Tuple:
        """
        ccc
        """

        def _outer_append(orders, side: str, prices: np.ndarray, sizes: np.ndarray):
            for i in range(prices.size):
                price = round_step_size(prices[i], self.tick_size)
                size = round_step_size(sizes[i], self.lot_size)
                orders.append([side, price, size])

        outer_orders = []
        _outer_append(outer_orders, "Buy", outer_prices[0], outer_quantities[0])
        _outer_append(outer_orders, "Sell", outer_prices[1], outer_quantities[1])

        return outer_orders


    def _generate_all_quotes(
        self
        ) -> Tuple:

        bid_skew, ask_skew = self._skew()
        target_inventory = bid_skew if bid_skew > ask_skew else -ask_skew

        inner_quotes = self._generate_inner_orders(
            inner_prices=self._inner_prices(bid_skew, ask_skew),
            inner_quantities=self._inner_quantities(bid_skew, ask_skew)
        )

        outer_quotes = self._generate_outer_quotes(
            outer_prices=self._outer_prices(),
            outer_quantities=self._outer_quantities()
        )

        return inner_quotes, outer_quotes, target_inventory

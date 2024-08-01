from typing import List
from numba.types import Array

from frameworks.tools.numba import nbclip, nbgeomspace, nbsqrt
from frameworks.tools.trading.weights import generate_geometric_weights
from smm.sharedstate import SmmSharedState
from smm.quote_generators.base import (
    QuoteGenerator, 
    Side, 
    TimeInForce, 
    OrderType, 
    Order
)


class PlainQuoteGenerator(QuoteGenerator):
    """
    This strategy's breakdown can be found in [smm/quote_generators/README.md]
    """
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
        super().__init__(self.ss)

    def corrected_skew(self, skew: float) -> float:
        """
        Calculate and return the skew value corrected for current inventory.

        Parameters
        ----------
        skew : float
            The original skew value.

        Returns
        -------
        float
            The corrected skew value.
        """
        corrective_amount = nbsqrt(self.inventory_delta)
        skew += -corrective_amount
        return skew

    def corrected_spread(self, spread: float) -> float:
        """
        Adjust the spread based on the minimum spread parameter.

        Parameters
        ----------
        spread : float
            The original spread value.

        Returns
        -------
        float
            The adjusted spread value.
        """
        min_spread = self.bps_to_decimal(self.params["minimum_spread"])
        return nbclip(spread, min_spread, min_spread * 5.0)

    def prepare_orders(
        self, bid_prices: Array, bid_sizes: Array, ask_prices: Array, ask_sizes: Array
    ) -> List[Order]:
        """
        Generates bid and ask orders with specified prices and sizes.
        The orders are generated in an alternating manner to prioritize inner orders
        (closer to the mid-price) and decrease priority outward.

        Steps
        -----
        1. Initialize an empty list to store orders and set the initial order level to 0.
        2. Loop through the provided bid prices, bid sizes, ask prices, and ask sizes:
            a. Generate a two-digit string representation of the current level.
            b. Create and append a bid order using the current bid price, bid size, and generated order ID.
            c. Create and append an ask order using the current ask price, ask size, and generated order ID.
            d. Increment the level for the next set of orders.
        3. Return the list of generated orders.

        Parameters
        ----------
        bid_prices : Array
            Array of bid prices.

        bid_sizes : Array
            Array of bid sizes.

        ask_prices : Array
            Array of ask prices.

        ask_sizes : Array
            Array of ask sizes.

        Returns
        -------
        List[Order]
            List of Orders.
        """
        orders = []
        level = 0

        for bid_price, bid_size, ask_price, ask_size in zip(
            bid_prices, bid_sizes, ask_prices, ask_sizes
        ):  
            str_level = str(level).zfill(2)

            orders.append(
                self.generate_single_quote(
                    side=Side.BUY,
                    orderType=OrderType.LIMIT,
                    timeInForce=TimeInForce.POST_ONLY,
                    price=self.round_bid(bid_price),
                    size=self.round_size(bid_size),
                    clientOrderId=self.orderid.generate_order_id(end=str_level)
                )
            )

            orders.append(
                self.generate_single_quote(
                    side=Side.SELL,
                    orderType=OrderType.LIMIT,
                    timeInForce=TimeInForce.POST_ONLY,
                    price=self.round_bid(ask_price),
                    size=self.round_size(ask_size),
                    clientOrderId=self.orderid.generate_order_id(end=str_level)
                )
            )

            level += 1

        return orders

    def generate_positive_skew_quotes(self, skew: float, spread: float) -> List[Order]:
        """
        Generate positively skewed bid/ask quotes, with the intention to fill
        more on the bid side (buy more) than the ask side (sell less).

        Steps
        -----
        1. Correct the spread to ensure it is within acceptable bounds.
        2. Calculate half of the corrected spread.
        3. Compute aggressiveness based on the provided skew.
        4. Determine the best bid and ask prices using the mid-price, half spread, and aggressiveness.
        5. Generate geometric sequences for bid and ask prices.
        6. Clip the skew to a maximum value to maintain a valid geometric ratio.
        7. Generate bid and ask sizes using geometric weights.
        8. Prepare and return the list of orders using the calculated prices and sizes.

        Parameters
        ----------
        skew : float
            A value > 0 predicting the future price over some time horizon.

        spread : float
            A value in dollars of minimum price deviation over some time horizon.

        Returns
        -------
        List[Order]
            A list of Orders.
        """
        corrected_spread = self.corrected_spread(spread)
        half_spread = corrected_spread / 2.0
        aggressiveness = self.params["aggressiveness"] * nbsqrt(skew)

        best_bid_price = self.mid_price - (half_spread * (1.0 - aggressiveness))
        best_ask_price = best_bid_price + corrected_spread

        bid_prices = nbgeomspace(
            start=best_bid_price,
            end=best_bid_price - (corrected_spread * 5.0),
            n=self.total_orders // 2,
        )

        ask_prices = nbgeomspace(
            start=best_ask_price,
            end=best_ask_price + (corrected_spread * 5.0),
            n=self.total_orders // 2,
        )

        clipped_r = 0.5 + nbclip(skew, 0.0, 0.5)  # NOTE: Geometric ratio cant exceed 1.0

        bid_sizes = self.max_position * generate_geometric_weights(
            num=self.total_orders // 2, r=clipped_r, reverse=True
        )

        ask_sizes = self.max_position * generate_geometric_weights(
            num=self.total_orders // 2,
            r=clipped_r ** (2.0 + aggressiveness),
            reverse=False,
        )

        return self.prepare_orders(bid_prices, bid_sizes, ask_prices, ask_sizes)

    def generate_negative_skew_quotes(self, skew: float, spread: float) -> List[Order]:
        """
        Generate negatively skewed bid/ask quotes, with the intention to fill
        more on the ask side (sell more) than the bid side (buy less).

        Steps
        -----
        1. Correct the spread to ensure it is within acceptable bounds.
        2. Calculate half of the corrected spread.
        3. Compute aggressiveness based on the absolute value of the skew.
        4. Determine the best ask and bid prices using the mid-price, half spread, and aggressiveness.
        5. Generate geometric sequences for bid and ask prices.
        6. Clip the absolute skew to a maximum value to maintain a valid geometric ratio.
        7. Generate bid and ask sizes using geometric weights.
        8. Prepare and return the list of orders using the calculated prices and sizes.

        Parameters
        ----------
        skew : float
            A value between -1 <-> 1 predicting the future price over some time horizon.

        spread : float
            A value in dollars of minimum price deviation over some time horizon.

        Returns
        -------
        List[Order]
            A list of Orders.
        """
        corrected_spread = self.corrected_spread(spread)
        half_spread = corrected_spread / 2.0
        aggressiveness = self.params["aggressiveness"] * nbsqrt(abs(skew))

        best_ask_price = self.mid_price + (half_spread * (1.0 - aggressiveness))
        best_bid_price = best_ask_price - corrected_spread

        bid_prices = nbgeomspace(
            start=best_bid_price,
            end=best_bid_price - (corrected_spread * 5.0),
            n=self.total_orders // 2,
        )

        ask_prices = nbgeomspace(
            start=best_ask_price,
            end=best_ask_price + (corrected_spread * 5.0),
            n=self.total_orders // 2,
        )

        clipped_r = 0.5 + nbclip(abs(skew), 0.0, 0.5) # NOTE: Geometric ratio cant exceed 1.0

        bid_sizes = self.max_position * generate_geometric_weights(
            num=self.total_orders // 2,
            r=clipped_r ** (2.0 + aggressiveness),
            reverse=True,
        )

        ask_sizes = self.max_position * generate_geometric_weights(
            num=self.total_orders // 2, r=clipped_r, reverse=False
        )

        return self.prepare_orders(bid_prices, bid_sizes, ask_prices, ask_sizes)

    def generate_orders(self, skew: float, spread: float) -> List[Order]:
        if skew >= 0.0:
            return self.generate_positive_skew_quotes(skew, spread)
        else:
            return self.generate_negative_skew_quotes(skew, spread)

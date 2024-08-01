from typing import List, Union

from frameworks.tools.logging import time_ms
from frameworks.tools.numba import nbgeomspace
from frameworks.tools.trading.weights import generate_geometric_weights
from smm.sharedstate import SmmSharedState
from smm.quote_generators.base import (
    QuoteGenerator, 
    Side, 
    TimeInForce, 
    OrderType, 
    Order,
    Position
)


class StinkyQuoteGenerator(QuoteGenerator):
    """
    This strategy's breakdown can be found in [smm/quote_generators/README.md]
    """
    def __init__(self, ss: SmmSharedState) -> None:
        super().__init__(ss)
        
        self.local_position = Position()
        self.local_position_time = 0.0

    def generate_stinky_orders(self) -> List[Order]:
        """
        Generate deep orders in a range from the base spread to base^1.5 away from mid.

        Steps
        -----
        1. Convert the base spread from basis points to a decimal.
        2. Generate geometric sequences for spreads and sizes:
            a. The spreads range from the base spread to the base spread raised to the power of 1.5.
            b. The sizes are generated using geometric weights.
        3. For each spread and size pair:
            a. Calculate the bid price by subtracting the spread from the mid-price.
            b. Calculate the ask price by adding the spread to the mid-price.
        4. Generate and append a bid order:
            a. Use the calculated bid price and size.
            b. Assign a client order ID with the level suffix.
        5. Generate and append an ask order:
            a. Use the calculated ask price and size.
            b. Assign a client order ID with the level suffix.

        Parameters
        ----------
        None

        Returns
        -------
        List[Order]
            A list of orders.
        """
        orders: List[Order] = []
        level = 0

        spreads = nbgeomspace(
            start=self.bps_to_decimal(self.params["base_spread"]),
            end=self.bps_to_decimal(self.params["base_spread"] ** 1.5),
            n=self.total_orders//2
        )

        sizes = self.max_position * generate_geometric_weights(num=self.total_orders//2)

        for spread, size in zip(spreads, sizes):
            bid_price = self.mid_price - spread
            ask_price = self.mid_price + spread

            str_level = str(level).zfill(2)

            orders.append(
                self.generate_single_quote(
                    side=Side.BUY,
                    orderType=OrderType.LIMIT,
                    timeInForce=TimeInForce.POST_ONLY,
                    price=self.round_bid(bid_price),
                    size=self.round_size(size),
                    clientOrderId=self.orderid.generate_order_id(end=str_level)
                )
            )

            orders.append(
                self.generate_single_quote(
                    side=Side.SELL,
                    orderType=OrderType.LIMIT,
                    timeInForce=TimeInForce.POST_ONLY,
                    price=self.round_bid(ask_price),
                    size=self.round_size(size),
                    clientOrderId=self.orderid.generate_order_id(end=str_level)
                )
            )

        return orders

    def position_executor(self, max_duration: float=10.0) -> List[Union[Order, None]]:
        """
        Purge a position if its duration exceeds a value.

        This method checks if the current position's duration exceeds a specified 
        maximum duration. If it does, it generates a taker order to exit the position.

        Steps
        -----
        1. If a position exists, save a copy locally of the first known state.
        2. Wait until 'max_duration' seconds have elapsed.
        3. Exit the position with t+X size, getting rid of all delta.
        4. Clear the local position and reset the cycle.

        Parameters
        ----------
        max_duration : float, optional
            The maximum duration in seconds before purging the position, by default 10.0.

        Returns
        -------
        List[Union[Order, None]]
            A list containing either a single taker order, or an empty list if no order is generated.
        """
        order: List[Union[Order, None]] = []

        if not self.data["position"].is_empty:
            if not self.local_position:
                self.local_position.update(self.data["position"])
                self.local_position_time = time_ms()

            else:
                max_duration_ms = self.local_position_time + (max_duration * 1000.0)
            
                if max_duration_ms < time_ms():
                    order.append(self.generate_single_quote(
                        side=Side.SELL if self.data["position"].size > 0.0 else Side.BUY,    
                        orderType=OrderType.MARKET,
                        timeInForce=TimeInForce.GTC,
                        size=self.data["position"].size,
                        clientOrderId=self.orderid.generate_order_id(end="99")
                    ))

                self.local_position.reset()
                self.local_position_time = 0.0
            
        return order

    def generate_orders(self, fp_skew: float, vol: float) -> List[Order]:
        return self.position_executor() + self.generate_stinky_orders()

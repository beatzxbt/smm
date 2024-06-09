from typing import Dict, List, Union

from frameworks.tools.logging import time_ms
from frameworks.tools.numba import nbgeomspace
from frameworks.tools.trading.weights import generate_geometric_weights
from smm.quote_generators.base import QuoteGenerator
from smm.sharedstate import SmmSharedState


class StinkyQuoteGenerator(QuoteGenerator):
    """
    This strategy's breakdown can be found in quote_generators.md
    """
    def __init__(self, ss: SmmSharedState) -> None:
        super().__init__(ss)
        
        self.local_position = {}
        self.local_position_time = 0.0

    def generate_stinky_orders(self) -> List[Dict]:
        """
        Generate deep orders in a range from the base spread to base^1.5 away from mid.

        This method generates a series of bid and ask orders based on geometric spreads 
        and sizes, ranging from base spread to a spread raised to the power of 1.5.

        Returns
        -------
        List[Dict]
            A list of single quotes.
        """
        orders = []
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
                    side=0,
                    orderType=0,
                    price=self.round_bid(bid_price),
                    size=self.round_size(size),
                    clientOrderId=self.orderid.generate_order_id(end=str_level)
                )
            )

            orders.append(
                self.generate_single_quote(
                    side=1,
                    orderType=0,
                    price=self.round_ask(ask_price),
                    size=self.round_size(size),
                    clientOrderId=self.orderid.generate_order_id(end=str_level)
                )
            )

    def position_executor(self, max_duration: float=5.0) -> List[Union[Dict, None]]:
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
        List[Union[Dict, None]]
            A list containing a single taker order, or an empty list if no order is generated.
        """
        order = []

        if self.data["position"].get(["size"], 0.0) != 0.0:
            if not self.local_position:
                self.local_position.update(self.data["position"])
                self.local_position_time = time_ms()

            else:
                max_duration_ms = self.local_position_time + (max_duration * 1000.0)
            
                if max_duration_ms < time_ms():
                    order.append(self.generate_single_quote(
                        side=1 if self.data["position"]["size"] > 0.0 else 0,    
                        orderType=1,
                        price=self.mid_price, # NOTE: Ignored value for takers
                        size=self.data["position"]["size"],
                        clientOrderId=self.orderid.generate_order_id(end="00")
                    ))

                self.local_position.clear()
                self.local_position_time = 0.0
            
        return order

    def generate_orders(self, fp_skew: float, vol: float) -> List[Dict]:
        return self.position_executor() + self.generate_stinky_orders()

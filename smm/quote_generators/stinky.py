from typing import List, Tuple

from frameworks.tools.logging import time_ms
from frameworks.tools.numba import nbgeomspace
from frameworks.tools.trading.rounding import round_ceil, round_floor
from frameworks.tools.trading.weights import generate_geometric_weights
from smm.quote_generators.base import QuoteGenerator
from smm.sharedstate import SmmSharedState


class StinkyQuoteGenerator(QuoteGenerator):
    """
    This strategy's breakdown can be found in quote_generators.md
    """
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
        super().__init__(self.ss)

    def generate_stinky_orders(self) -> List[Tuple]:
        """
        Generate deep orders in a range from the base spread to base^1.5 away from mid

        Returns
        -------
        List[Tuple]
            A list of single quotes.
        """
        orders = []

        spreads = nbgeomspace(
            start=self.bps_to_decimal(self.params["base_spread"]),
            end=self.bps_to_decimal(self.params["base_spread"] ** 1.5),
            n=self.total_orders//2
        )

        sizes = self.max_position * generate_geometric_weights(num=self.total_orders//2)

        for spread, size in zip(spreads, sizes):
            orders.append(
                self.generate_single_quote(
                    side=0.0,
                    orderType=0.0,
                    price=round_floor(num=self.wmid - spread, step_size=self.tick_size),
                    size=round_ceil(num=size, step_size=self.lot_size),
                )
            )

            orders.append(  
                self.generate_single_quote(
                    side=1.0,
                    orderType=0.0,
                    price=round_ceil(num=self.wmid + spread, step_size=self.tick_size),
                    size=round_ceil(num=size, step_size=self.lot_size),
                )
            )

    def inventory_executor(self, max_duration: float=10.0) -> List[Tuple]:
        """Purge inventory if its duration exceeds a value"""
        order = []

        if self.ss.current_position:
            max_duration_ms = self.ss.current_position["time"] + (max_duration * 1000)
            
            if max_duration_ms < time_ms():
                order.append(self.generate_single_quote(
                    side=1.0 if self.ss.current_position["size"] > 0.0 else 0.0,    
                    orderType=1.0,
                    price=self.mid, # NOTE: Ignored value for takers
                    size=self.ss.current_position["size"] # NOTE: Assumes position is always in correct lot size
                ))
            
        return order

    def generate_quotes(self, skew: float, spread: float) -> List[Tuple]:
        return self.inventory_executor() + self.generate_stinky_orders()

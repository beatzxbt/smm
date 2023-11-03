
import asyncio
import numpy as np

from frameworks.exchange.bybit.post.order import BybitOrder
from frameworks.tools.numba_funcs import nabs
from frameworks.tools.rounding import round_step_size
from frameworks.tools.logging.logger import Logger
from frameworks.sharedstate.market import MarketDataSharedState
from frameworks.sharedstate.private import PrivateDataSharedState

from stink_biddor.strategy.arb import StinkBiddor
from stink_biddor.settings import StrategyParameters


class Strategy:


    def __init__(
        self, 
        mdss: MarketDataSharedState, 
        pdss: PrivateDataSharedState,
        strategy_params: StrategyParameters
    ) -> None:

        self.mdss = mdss
        self.pdss = pdss
        self.strategy = strategy_params
        self.symbol = self.strategy.symbol

        self.logging = Logger()
        self.sleep_timer = 30


    async def _max_pos_check(self) -> None:
        curr_pos = self.pdss.bybit["Data"][self.symbol]["position_size"]

        # If position exists, market out (assumes TP isnt filling in time)
        if nabs(curr_pos) > 0:
            self.logging.info(f"Outstanding delta of {curr_pos}, neutralizing...")
            side = "Buy" if curr_pos < 0 else "Sell"
            qty = round_step_size(nabs(curr_pos), self.mdss.bybit[self.symbol]["tick_size"])
            await BybitOrder(self.pdss, self.symbol).order_market((side, qty))
            self.pdss.bybit["Data"][self.symbol]["position_size"] = 0


    async def _max_order_check(self) -> None:
        num_orders = len(self.pdss.bybit["Data"][self.symbol]["current_orders"])

        # If any orders, reset to empty state (no orders)
        if num_orders > 0:
            await BybitOrder(self.pdss, self.symbol).cancel_all()

        
    async def run(self) -> None:
        self.logging.info("Warming up data feeds...")
        await asyncio.sleep(5)

        self.logging.info(f"Starting strategy with {len(self.strategy.stink_levels) * 2} levels...")

        while True:
            # Perform checks before starting new iteration
            await self._max_order_check()
            await self._max_pos_check()
            await asyncio.sleep(0.5)
            
            tasks = []

            # Spawn individual tasks for different levels
            for levels in self.strategy.stink_levels:
                tasks.append(asyncio.create_task(StinkBiddor(self.mdss, self.pdss, self.symbol, levels).buy()))
                tasks.append(asyncio.create_task(StinkBiddor(self.mdss, self.pdss, self.symbol, levels).sell()))

            await asyncio.sleep(self.sleep_timer)
            
            # Cancel each task and reset
            for task in tasks:
                task.cancel()

            await asyncio.sleep(0.5)


import asyncio

from frameworks.tools.misc import current_datetime as now
from frameworks.tools.logging.logger import Logger
from smm.strategy.quote_generators.basic import BasicQuoteGenerator
from smm.settings import StrategyParameters
from smm.strategy.diff import Diff

from frameworks.sharedstate.market import MarketDataSharedState
from frameworks.sharedstate.private import PrivateDataSharedState


class DataFeeds:


    def __init__(self) -> None:
        pass
        


class MarketMaker:


    def __init__(
        self, 
        mdss: MarketDataSharedState, 
        pdss: PrivateDataSharedState
    ) -> None:

        self.mdss = mdss
        self.pdss = pdss
        self.params  = StrategyParameters()
        self.logger = Logger()


    async def logic(self):
        # Small delay to allow data arrays to initialize
        self.logger.info("Warming up data feeds...")
        await asyncio.sleep(5)

        self.logger.info("Starting strategy...")
        
        while True:
            # Pause for 10ms to let websockets to process data
            await asyncio.sleep(0.01 * 100) # 1s override for now
            
            new_orders = BasicQuoteGenerator(
                mdss=self.mdss,
                pdss=self.pdss,
                strategy_params=StrategyParameters()
            )
            
            # Diff function will manage new order placements, if any
            await Diff(self.ss).diff(new_orders)


    async def run(self):
        await self.logic()
    
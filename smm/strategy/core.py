import asyncio
from frameworks.sharedstate import SharedState
from smm.strategy.quote_generators.simple import SimpleQuoteGenerator
from smm.strategy.quote_generators.basic import BasicQuoteGenerator
from smm.settings import SmmParameters
from smm.strategy.diff import Diff


class MarketMaker:

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.params  = SmmParameters()
        self.logger = self.ss.logging

        self.quote_generator = None

    def _strategy_selector_(self) -> None:
        if self.quote_generator is None:
            if self.params["quote_generator"] == "simple":
                self.quote_generator = SimpleQuoteGenerator(self.ss, self.params["simple"])

    async def _loop_(self):
        self.logger.info("Warming up data feeds...")
        await asyncio.sleep(5)

        self.logger.info(f"Starting {self.params['quote_generator']} strategy...")
        
        while True:
            await asyncio.sleep(0.01 * 100)
            
            # Add a switch here to let user swap between strategies (in realtime)
            new_orders = self.quote_generator(self.ss, self.params)
            
            await Diff(self.ss).diff(new_orders)


    async def run(self):
        await asyncio.gather(
            await self.params.refresh_parameters(),
            await self._loop_()
        )
    
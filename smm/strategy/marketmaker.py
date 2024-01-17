import asyncio
from frameworks.sharedstate import SharedState
from smm.settings import SmmParameters
from smm.strategy.oms import OrderManagementSystem


class MarketMaker:

    def __init__(self, ss: SharedState, params: SmmParameters) -> None:
        self.ss = ss
        self.params = params
        self.logger = self.ss.logging

        self.quote_generator = None
        self.oms = OrderManagementSystem(self.ss)

    def _strategy_selector_(self) -> None:
        if self.quote_generator is None:
            if self.params["quote_generator"] == "simple":
                from smm.strategy.quote_generators.simple import SimpleQuoteGenerator
                self.quote_generator = SimpleQuoteGenerator(self.ss, self.params["simple"])

            elif self.params["quote_generator"] == "basic":
                from smm.strategy.quote_generators.basic import BasicQuoteGenerator
                self.quote_generator = BasicQuoteGenerator(self.ss, self.params["basic"])

    async def _loop_(self):
        self.logger.info("Warming up data feeds...")
        await asyncio.sleep(5)

        self.logger.info(f"Starting {self.params['quote_generator']} strategy...")
        
        while True:
            await asyncio.sleep(0.01 * 100)
            new_orders = self.quote_generator.generate_quotes()
            await self.oms.update(new_orders)

    async def run(self):
        await asyncio.gather(
            await self.params.refresh_parameters(),
            await self._loop_()
        )
    
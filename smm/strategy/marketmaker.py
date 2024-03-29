import asyncio
from typing import Any 
from frameworks.datafeed import DataFeed
from smm.sharedstate import SmmSharedState
from smm.oms.oms import OrderManagementSystem


class TradingLogic:
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
        self.quote_generator = None
        self.ws_feed = DataFeed(self.ss)
        self.oms = OrderManagementSystem(self.ss)

    def _load_quote_generator_(self) -> Any:
        if self.params["quote_generator"] == "simple":
            from smm.quote_generators.simple import SimpleQuoteGenerator
            return SimpleQuoteGenerator(self.ss)

        elif self.params["quote_generator"] == "basic":
            from smm.quote_generators.basic import BasicQuoteGenerator
            return BasicQuoteGenerator(self.ss)

    async def start_loop(self):
        self.ss.logging.info("Warming up data feeds...")
        await asyncio.sleep(5)

        self.ss.logging.info(f"Starting {self.params['quote_generator']} strategy...")
        
        while True:
            await asyncio.sleep(0.01 * 100)
            new_orders = self.quote_generator.generate_quotes()
            await self.oms.update(new_orders)
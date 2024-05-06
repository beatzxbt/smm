import asyncio

from smm.sharedstate import SmmSharedState
from smm.quote_generators.base import QuoteGenerator
from smm.oms.oms import OrderManagementSystem


class TradingLogic:
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
        self.quote_generator = self.load_quote_generator()
        self.oms = OrderManagementSystem(self.ss)

    def load_quote_generator(self) -> QuoteGenerator:
        if str(self.params["quote_generator"]).lower() == "plain":
            from smm.quote_generators.plain import PlainQuoteGenerator
            return PlainQuoteGenerator(self.ss)
        
        elif str(self.params["quote_generator"]).lower() == "stinky":
            from smm.quote_generators.stinky import StinkyQuoteGenerator
            return StinkyQuoteGenerator(self.ss)

    async def wait_for_ws_warmup(self) -> None:
        """
        Waits for confirmation that the WebSocket connections are 
        established and data is filling the arrays.
        """
        while True: 
            await asyncio.sleep(1)

            if self.ss.trades.shape[0] < 100:
                continue

            if self.ss.ohlcv.shape[0] < 100:
                continue

            if not bool(self.ss.ticker):
                continue

            if tuple(self.ss.misc.values()) == (0.0, 0.0):
                continue

            break

    async def start_loop(self) -> None:
        await self.ss.logging.info("Warming up data feeds...")
        await self.wait_for_ws_warmup()
        await self.ss.logging.success(
            f"Starting {self.params['quote_generator']} strategy on {self.ss.exchange.upper()} | {self.ss.symbol}"
        )
        
        while True:
            await asyncio.sleep(0.01 * 100)
            new_orders = self.quote_generator.generate_quotes()
            await self.oms.update(new_orders)
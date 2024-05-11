import asyncio

from smm.sharedstate import SmmSharedState
from smm.quote_generators.base import QuoteGenerator
from smm.oms.oms import OrderManagementSystem
from smm.features.features import FeatureEngine


class TradingLogic:
    def __init__(self, ss: SmmSharedState) -> None:
        self.ss = ss
        self.feature_engine = FeatureEngine(self.ss)
        self.quote_generator = self.load_quote_generator()
        self.oms = OrderManagementSystem(self.ss)

    async def load_quote_generator(self) -> QuoteGenerator:
        quote_gen_name = self.params["quote_generator"].lower()
        
        match quote_gen_name:
            case "plain":
                from smm.quote_generators.plain import PlainQuoteGenerator
                return PlainQuoteGenerator(self.ss)
            
            case "stinky":
                from smm.quote_generators.stinky import StinkyQuoteGenerator
                return StinkyQuoteGenerator(self.ss)
            
            case _:
                await self.ss.logging.error(f"Invalid quote generator, double check available options!")
                raise ValueError(f"Invalid quote generator: {quote_gen_name}")
            
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
            await asyncio.sleep(1.0)
            fp_skew = self.feature_engine.generate_skew()
            vol = self.feature_engine.generate_vol()
            new_orders = self.quote_generator.generate_orders(fp_skew, vol)
            await self.oms.update(new_orders)
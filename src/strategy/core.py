
import asyncio

from src.utils.misc import curr_dt
from src.strategy.ws_feeds.bybitmarketdata import BybitMarketData
from src.strategy.ws_feeds.binancemarketdata import BinanceMarketData
from src.strategy.ws_feeds.bybitprivatedata import BybitPrivateData
from src.strategy.marketmaker import MarketMaker
from src.strategy.diff import Diff

from src.sharedstate import SharedState


class DataFeeds:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    async def start_feeds(self) -> None:

        tasks = [
            asyncio.create_task(BybitMarketData(self.ss).start_feed()),
            asyncio.create_task(BybitPrivateData(self.ss).start_feed())
        ]

        if self.ss.primary_data_feed == "BINANCE":
            tasks.append(
                asyncio.create_task(BinanceMarketData(self.ss).start_feed())
            )

        await asyncio.gather(*tasks)



class Strategy:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    async def logic(self):
        
        # Delay to let data feeds warm up
        print(f"{curr_dt()}: Warming up data feeds...")
        await asyncio.sleep(10)

        print(f"{curr_dt()}: Starting strategy...")
        
        while True:
            
            # Pause for 10ms to let data feeds update
            await asyncio.sleep(0.01 * 100)
            
            # Generate new orders
            new_orders = MarketMaker(self.ss).generate_quotes()
            
            # Diff function will manage new order placements, if any
            await Diff(self.ss).diff(new_orders)


    async def run(self):
        await asyncio.gather(
            asyncio.create_task(DataFeeds(self.ss).start_feeds()),
            asyncio.create_task(self.logic())
        )
    
import asyncio

from src.utils.jit_funcs import nabs

from src.strategy.ws_feeds.bybitmarketdata import BybitMarketData
from src.strategy.ws_feeds.binancemarketdata import BinanceMarketData
from src.strategy.ws_feeds.bybitprivatedata import BybitPrivateData
from src.strategy.binance.binance_mm import MarketMaker
from src.strategy.diff import Diff

from src.sharedstate import SharedState


class DataFeeds:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    async def start_feeds(self) -> None:

        tasks = []

        # Start all ws feeds as tasks, updating the sharedstate in the background \
        bin_pub_data = BinanceMarketData(self.ss).start_feed()
        bybit_pub_data = BybitMarketData(self.ss).start_feed()
        bybit_priv_data = BybitPrivateData(self.ss).start_feed()

        tasks.append(asyncio.create_task(bin_pub_data, name="BinanceMarketData"))
        tasks.append(asyncio.create_task(bybit_pub_data, name="BybitMarketData"))
        tasks.append(asyncio.create_task(bybit_priv_data, name="BybitPrivateData"))

        # Run strategy #
        await asyncio.gather(*tasks)



class Strategy:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    async def logic(self):
        
        # Delay to let data feeds warm up \
        print('Warming up data feeds...')
        await asyncio.sleep(10)

        print('Starting strategy...')
        
        while True:
            
            # Pause for 5ms to let data feeds update \
            await asyncio.sleep(0.005)
            
            # Generate new orders \
            new_orders = MarketMaker(self.ss).market_maker()
            
            # Diff function will manage new order placements, if any \
            await Diff(self.ss).diff(new_orders)


    async def run(self):

        tasks = []

        # Start all ws feeds \
        tasks.append(asyncio.create_task(DataFeeds(self.ss).start_feeds()))

        # Add the strategy task to the tasks list \
        tasks.append(asyncio.create_task(self.logic(), name="Strategy"))

        # Run strategy #
        await asyncio.gather(*tasks)
    
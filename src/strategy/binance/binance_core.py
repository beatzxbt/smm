import asyncio

from src.strategy.ws_feeds.bybitmarketdata import BybitMarketData
from src.strategy.ws_feeds.binancemarketdata import BinanceMarketData
from src.strategy.ws_feeds.bybitprivatedata import BybitPrivateData

from src.strategy.binance.binance_mm import MarketMaker
from src.bybit.order.core import Order
from src.utils.rounding import round_step_size



class DataFeeds:


    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate


    async def start_feeds(self) -> None:

        tasks = []

        # Start all ws feeds as tasks, updating the sharedstate in the background \
        bybit_priv_data = BybitPrivateData(self.ss).start_feed()
        bin_pub_data = BinanceMarketData(self.ss).start_feed()
        bybit_pub_data = BybitMarketData(self.ss).start_feed()

        tasks.append(asyncio.create_task(bybit_priv_data, name="BybitPrivateData"))
        tasks.append(asyncio.create_task(bin_pub_data, name="BinanceMarketData"))
        tasks.append(asyncio.create_task(bybit_pub_data, name="BybitMarketData"))

        # Run strategy #
        await asyncio.gather(*tasks)



class Strategy:


    def __init__(self, sharedstate) -> None:
        self.ss = sharedstate

        # This will be a snapshot of the previous price \
        self.previous_price = self.fair_price_update()


    def fair_price_update(self):

        # Update the snapshot to the latest version \
        benchmark = self.ss.binance_mid_price
        step_size = self.ss.buffer_multiplier

        new_price = round_step_size(benchmark, step_size)

        return new_price


    async def logic(self):
        
        # Delay to let data feeds warm up \
        print('Warming up data feeds...')
        await asyncio.sleep(10)

        print('Starting strategy...')
        
        while True:
            
            # Pause while loop to let data feeds update \
            await asyncio.sleep(0.01)
            
            curr_price = self.fair_price_update()

            # Executes strategy only if previous state price changes \
            if curr_price != self.previous_price:
                
                cancel = await Order(self.ss).cancel_all()

                quotes = MarketMaker(self.ss).market_maker()

                order = await Order(self.ss).submit_batch(quotes)

                # Update the previous fair price \
                self.previous_price = curr_price


    async def run(self):

        tasks = []

        # Start all ws feeds \
        tasks.append(asyncio.create_task(DataFeeds(self.ss).start_feeds()))

        # Add the strategy task to the tasks list \
        tasks.append(asyncio.create_task(self.logic(), name="Strategy"))

        # Run strategy #
        await asyncio.gather(*tasks)
    
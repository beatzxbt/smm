import asyncio
from typing import Coroutine
from src.utils.misc import datetime_now as dt_now
from src.strategy.ws_feeds.bybitmarketdata import BybitMarketData
from src.strategy.ws_feeds.binancemarketdata import BinanceMarketData
from src.strategy.ws_feeds.bybitprivatedata import BybitPrivateData
from src.strategy.marketmaker import MarketMaker
from src.strategy.oms import OMS
from src.sharedstate import SharedState


class DataFeeds:
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss

    async def start_feeds(self) -> Coroutine:
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
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss

    async def _wait_for_ws_confirmation_(self) -> Coroutine:
        while True: 
            await asyncio.sleep(1)
            if self.ss.primary_data_feed == "BINANCE":
                if self.ss.bybit_ws_connected and self.ss.binance_ws_connected:
                    break
            else:
                if self.ss.bybit_ws_connected: 
                    break
                
    async def primary_loop(self) -> None:
        print(f"{dt_now()}: Starting data feeds...")
        await self._wait_for_ws_confirmation_()
        print(f"{dt_now()}: Starting strategy...")
        
        while True:
            await asyncio.sleep(1)
            new_orders, spread = MarketMaker(self.ss).generate_quotes(debug=True)
            await OMS(self.ss).run(new_orders, spread)

    async def run(self) -> Coroutine:
        await asyncio.gather(
            asyncio.create_task(DataFeeds(self.ss).start_feeds()),
            asyncio.create_task(self.primary_loop())
        )
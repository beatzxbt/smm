import asyncio

from src.strategy.bybit.bybit_core import Strategy as BybitStrategy
from src.strategy.binance.binance_core import Strategy as BinanceStrategy

from src.sharedstate import SharedState


async def main():

    sharedstate = SharedState()
    
    tasks = []
    
    # Refresh parameters \
    tasks.append(asyncio.create_task(sharedstate.refresh_parameters()))

    # Add correct data feed and strategy choice \
    if sharedstate.primary_data_feed == 'BINANCE':
        tasks.append(asyncio.create_task(BinanceStrategy(sharedstate).run()))

    elif sharedstate.primary_data_feed == 'BYBIT':
        tasks.append(asyncio.create_task(BybitStrategy(sharedstate).run()))

    else:
        print("Invalid exchange selected, choices are 'BINANCE' or 'BYBIT'")
        raise NotImplementedError

    # Run tasks \
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())



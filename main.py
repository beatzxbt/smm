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

    if sharedstate.primary_data_feed == 'BYBIT':
        tasks.append(asyncio.create_task(BybitStrategy(sharedstate).run()))

    else:
        print('Invalid exchange selected, refer to README.md for correct names!')
        raise

    # Run tasks \
    await asyncio.gather(*tasks)


if __name__ == "__main__":
<<<<<<< Updated upstream

    # Copy the directory of the param .yaml file and paste it below \
    param_dir = ""
    config_dir = ""
    
    _run = asyncio.run(Main('BTCUSDT', config_dir, param_dir).strategy())


=======
    asyncio.run(main())
>>>>>>> Stashed changes



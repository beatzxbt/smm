
import asyncio
import argparse

from src.strategy.core import Strategy
from src.sharedstate import SharedState
from src.new_sharedstate import NewSharedState



async def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', 
                        help = "Sets the api key to use")
    parser.add_argument('-t', '--ticker', 
                        help = "Sets the ticker to use")
    parser.add_argument('-f', '--feed',
                        help = "Sets the default data feed")
    parser.add_argument('-sf', '--sizef',
                        help = "This uses a account size of the file itself")
    parser.add_argument('-s', '--size',
                        help = "This allows the user to set a account size from the arguments itself not needing the configuration file")
    parser.add_argument('-a', '--algo',
                        help = "This defines the strategy that the user want to use")
    parser.add_argument("-c", "--conf",
                        help = "This is the configuration of the strategy that the user want to use")
    
    args = parser.parse_args()

    ss = NewSharedState(
        args.key,
        args.ticker,
        args.feed,
        args.sizef,
        args.size,
        args.algo,
        args.conf
    )

    #
    ## Run tasks \
    await asyncio.gather(
        #asyncio.create_task(ss.refresh_parameters()),
        asyncio.create_task(Strategy(ss).run())
    )


if __name__ == "__main__":
    asyncio.run(main())


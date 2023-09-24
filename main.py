
import asyncio
import argparse

from src.strategy.core import Strategy
from src.sharedstate import SharedState
from src.new_sharedstate import NewSharedState



async def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', 
                        help = "Sets the api key to use",
                        default = "1")
    parser.add_argument('-t', '--ticker', 
                        help = "Sets the ticker to use",
                        default = "")
    args = parser.parse_args()


    ss = NewSharedState(
        args.key,
        args.ticker
    )

    #
    ## Run tasks \
    #await asyncio.gather(
    #    asyncio.create_task(sharedstate.refresh_parameters()),
    #    asyncio.create_task(Strategy(sharedstate).run())
    #)


if __name__ == "__main__":
    asyncio.run(main())


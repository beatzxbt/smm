
import asyncio
import argparse

from smm.strategy.core import Strategy
from frameworks.sharedstate.market import MarketDataSharedState
from frameworks.sharedstate.private import PrivateDataSharedState


async def main():

    market = MarketDataSharedState()
    private = PrivateDataSharedState()

    await asyncio.gather(
        asyncio.create_task(Strategy(ss).run())
    )


if __name__ == "__main__":
    asyncio.run(main())


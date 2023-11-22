
import asyncio

from smm.strategy.core import MarketMaker
from smm.settings import StrategyParameters
from frameworks.sharedstate.market import MarketDataSharedState
from frameworks.sharedstate.private import PrivateDataSharedState


async def main():
    CONFIG_DIR = ""
    PARAM_DIR = ""

    mdss = MarketDataSharedState()
    params = StrategyParameters(PARAM_DIR)
    pdss = PrivateDataSharedState(CONFIG_DIR)

    await MarketMaker(mdss, pdss, params).run()
    

if __name__ == "__main__":
    asyncio.run(main())


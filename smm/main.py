import asyncio
from smm.strategy.core import MarketMaker
from smm.settings import SmmParameters
from frameworks.sharedstate import SharedState


async def main():
    ss = SharedState()
    params = SmmParameters(ss)
    ss._load_markets_()
    await MarketMaker(ss).run()    


if __name__ == "__main__":
    asyncio.run(main())


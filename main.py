
import asyncio

from src.strategy.core import Strategy
from src.sharedstate import SharedState


async def main():

    sharedstate = SharedState()
    
    # Run tasks \
    await asyncio.gather(
        asyncio.create_task(sharedstate.refresh_parameters()),
        asyncio.create_task(Strategy(sharedstate).run())
    )


if __name__ == "__main__":
    asyncio.run(main())



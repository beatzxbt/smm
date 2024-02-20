import asyncio
import uvloop
from src.strategy.core import Strategy
from src.sharedstate import SharedState

async def main():
    sharedstate = SharedState()
    await asyncio.gather(
        asyncio.create_task(sharedstate.refresh_parameters()),
        asyncio.create_task(Strategy(sharedstate).run())
    )

if __name__ == "__main__":
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(main())
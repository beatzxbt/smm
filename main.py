import asyncio
import uvloop
from src.strategy.core import Strategy
from src.sharedstate import SharedState

async def main():
    """
    The main entry point of the application. Initializes the shared state and strategy,
    then concurrently refreshes parameters and runs the trading strategy.
    """
    sharedstate = SharedState()

    await asyncio.gather(
        asyncio.create_task(sharedstate.refresh_parameters()),  
        asyncio.create_task(Strategy(sharedstate).run())  
    )

if __name__ == "__main__":
    # Set uvloop as the event loop policy to enhance performance.
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(main())
import asyncio
from frameworks.sharedstate import SharedState
from frameworks.tools.logger import Logger, now
from smm.strategy.marketmaker import MarketMaker
from smm.settings import SmmParameters


async def main():
    try:
        parameters_directory = ""
        params = SmmParameters(parameters_directory)

        ss = SharedState()
        ss.load_markets(params.markets)

        await asyncio.gather(
            asyncio.to_thread(params.refresh_parameters()),
            asyncio.to_thread(MarketMaker(ss, params).run())
        )

    except Exception as e:
        Logger.critical(f"High level exception occurred, shutting down...")
        # TODO: Implement shut down routine without sharedstate use
        raise e

    finally:
        print(f"It's {now()}, goodnight...")
        
if __name__ == "__main__":
    asyncio.run(main())

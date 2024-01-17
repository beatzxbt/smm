import asyncio
from frameworks.sharedstate import SharedState
from stink_biddor.strategy.stinkbiddor import StinkBiddor
from stink_biddor.settings import StinkBiddorParameters
from frameworks.tools.logger import Logger, now


async def main():
    try:
        parameters_directory = ""
        params = StinkBiddorParameters(parameters_directory)

        ss = SharedState()
        ss.load_markets(params.pair)

        await asyncio.gather(
            asyncio.to_thread(params.refresh_parameters()),
            asyncio.to_thread(StinkBiddor(ss, params).run())
        )

    except Exception as e:
        Logger.critical(f"High level exception occurred, shutting down...")
        # TODO: Implement shut down routine without sharedstate use
        raise e

    finally:
        print(f"It's {now()}, goodnight...")
        
if __name__ == "__main__":
    asyncio.run(main())
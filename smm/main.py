import asyncio
import uvloop

from smm.strategy.marketmaker import TradingLogic
from smm.sharedstate import SmmSharedState


async def main():
    try:
        ss = SmmSharedState()
        trading_logic = TradingLogic(ss)

        await asyncio.gather(
            asyncio.create_task(ss.start_internal_processes()),
            asyncio.create_task(ss.refresh_parameters()),
            asyncio.create_task(trading_logic.start_loop()),
            return_exceptions=True,
        )

    except KeyboardInterrupt:
        await ss.logging.critical(f"Process manually interupted by user...")
        return None

    except Exception as e:
        await ss.logging.critical(f"Unexpected exception occurred: {e}")
        raise e

    finally:
        await ss.logging.critical("Starting shutdown sequence...")
        pass
        # Implement shutdown sequence here, and this should be included
        # in all exchange classes which does the following:
        #  -> Cancel all open orders
        #  -> Dump any existing position to market
        #
        # Then after:
        #  -> Cleanup background websocket/exchange related async tasks


if __name__ == "__main__":
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(main())

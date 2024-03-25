import asyncio
import uvloop
from frameworks.tools.logging import Logger
from smm.strategy.marketmaker import TradingLogic
from smm.sharedstate import SmmSharedState


async def main():
    try:
        backup_logger = Logger
        ss = SmmSharedState()
        trading_logic = TradingLogic(ss)

        await asyncio.gather(
            asyncio.create_task(ss.refresh_parameters()),
            asyncio.create_task(trading_logic.start_loop()),
            return_exceptions=True
        )

    except KeyboardInterrupt:
        backup_logger.critical(f"Process manually interupted by user...")
        return None

    except Exception as e:
        backup_logger.critical(f"Unexpected exception occurred: {e}")
        raise e

    finally:
        backup_logger.critical("Starting shutdown sequence...")
        pass
        # """
        # Implement shutdown sequence here with new sharedstate
        # It should:
        #     -> Cancel all open orders
        #     -> Dump any existing position to market
        #     -> Cleanup background async tasks 
        # """

if __name__ == "__main__":
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(main())

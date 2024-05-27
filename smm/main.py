import sys
import os

# Get the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root directory to the Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------------------------------------------- #

import asyncio

from frameworks.tools.asynchronous import initialize_event_loop
from smm.strategy.marketmaker import TradingLogic
from smm.sharedstate import SmmSharedState


    
async def main():
    try:
        ss = SmmSharedState()
        trading_logic = TradingLogic(ss)

        await asyncio.gather(
            ss.start_internal_processes(),
            ss.refresh_parameters(),
            trading_logic.start_loop()
        )

    except KeyboardInterrupt or asyncio.CancelledError:
        await ss.logging.critical(f"Process manually interupted by user...")
        raise 
    
    except Exception as e:
        await ss.logging.critical(f"Unexpected exception occurred: {e}")
        raise e

    finally:
        await ss.logging.critical("Starting shutdown sequence...")
        await ss.exchange.shutdown()
        await ss.logging.info("Goodnight...")
        await ss.logging.shutdown()

if __name__ == "__main__":
    initialize_event_loop()
    asyncio.run(main())

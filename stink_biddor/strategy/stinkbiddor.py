import asyncio
from frameworks.sharedstate import SharedState
from stink_biddor.strategy.levels import StinkLevels
from stink_biddor.strategy.safeties import StinkSafeties
from stink_biddor.settings import StinkBiddorParameters


class StinkBiddor:

    def __init__(self, ss: SharedState, params: StinkBiddorParameters) -> None:
        self.ss = ss
        self.pair, self.levels = params.pair, params.levels
        self.logging = self.ss.logging

        self.safety = StinkSafeties(self.ss, params)
        
    async def run(self) -> None:
        self.logging.info("Warming up data feeds & strategy monitoring loops...")
        asyncio.create_task(asyncio.to_thread(self.safety.monitor))
        await asyncio.sleep(5)

        self.logging.info(f"Starting strategy on {self.pair} with {len(self.levels) * 2} levels...")

        while True:
            tasks = []

            for level in self.levels:
                tasks.append(StinkLevels(self.ss, level).bid())
                tasks.append(StinkLevels(self.ss, level).ask())

            # Wait for tasks to complete and/or timer to expire
            done, pending = await asyncio.wait(tasks, timeout=self.sleep_timer)

            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
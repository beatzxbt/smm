import asyncio
from time import time
from frameworks.tools.rounding import round_step
from frameworks.sharedstate import SharedState
from stink_biddor.settings import StinkBiddorParameters
from typing import Dict, Union, Coroutine


class StinkSafeties:

    def __init__(self, ss: SharedState, params: StinkBiddorParameters) -> None:
        self.ss = ss
        self.exchange, self.symbol = params.pair
        self.levels = params.levels
        self.logging = self.ss.logging

        self.max_order_duration = self.set_max_order_duration()

        self.position_life = 0
        self.position_cache = {}

    @property
    def __market__(self) -> Dict:
        return self.ss.market[self.exchange][self.symbol]

    @property
    def __private__(self) -> Dict:
        return self.ss.private[self.exchange][self.symbol]

    @property
    def __client__(self):   
        return self.ss.clients[self.exchange]["order_client"]

    async def _post_market_(self, side: int, amount: float) -> Union[None, str]:
        """Hardcoded constant params to make core code cleaner, returns orderId"""
        await self.__client__.post_create_order(
            symbol=self.symbol,
            side=side,
            type="market",
            amount=round_step(amount, self.__market__["lotSize"])
        )

    async def set_max_order_duration(self, duration: int=10) -> None:
        self.max_order_duration = duration

    async def _position_neutralizer_(self) -> Coroutine:
        while True:
            cp = self.__private__["currentPosition"]

            if self.position_life != 0:
                duration = time() - self.position_life

                if duration < self.max_order_duration:
                    continue
                
                self.logging.info(f"Position of [{cp} | {duration}], neutralizing...")
                await self._post_market_(side=0 if cp < 0 else 1, amount=cp)
                await asyncio.sleep(1)
                self.position_life = 0

            elif cp != 0:
                self.position_life = time()
                
            else:
                await asyncio.sleep(0.1)

    async def _stale_order_checker_(self) -> Coroutine:
        max_orders = len(self.levels) * 4

        while True:
            if len(self.__private__["openOrders"]) > max_orders:
                self.logging.info(f"Max orders exceeded, cancelling all...")
                self.__client__.post_cancel_all()
                await asyncio.sleep(1)
            
            else:
                await asyncio.sleep(0.1)
        
    async def monitor(self) -> None:
        try:
            await asyncio.gather(
                self._position_neutralizer_(),
                self._stale_order_checker_()
            )

        except Exception as e:
            self.logging.error(f"Error with safety loop: {e}")
            raise e

        finally:
            self.logging.info(f"Cancelling all orders...")
            self.__client__.post_cancel_all()
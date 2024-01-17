import asyncio
from frameworks.tools.rounding import round_step
from frameworks.sharedstate import SharedState
from frameworks.tools.mids import mid
from typing import Tuple, List, Dict, Union


class StinkLevels:

    def __init__(self, ss: SharedState, pair: Tuple[str, str], level: List[float]) -> None:
        self.ss = ss
        self.exchange, self.symbol = pair
        self.entry_bps, self.exit_bps, self.qty = level
        self.logging = self.ss.logging

    @property
    def __market__(self) -> Dict:
        return self.ss.market[self.exchange][self.symbol]

    @property
    def __private__(self) -> Dict:
        return self.ss.private[self.exchange][self.symbol]

    @property
    def __client__(self):   
        return self.ss.clients[self.exchange]["order_client"]

    def _mid_(self) -> float:
        return mid(self.__market__["bba"]) 

    def _bid_(self) -> Tuple[float, float]:
        """Mid - entry & exit offset for bids"""
        entry = self.entry_bps / 10_000
        exit = self.exit_bps / 10_000
        return (
            round_step(self._mid_() * (1-entry), self.__market__["tickSize"]),
            round_step(self._mid_() * (1-exit), self.__market__["tickSize"])
        )

    def _ask_(self) -> Tuple[float, float]:
        """Mid - entry & exit offset for asks"""
        entry = self.entry_bps / 10_000
        exit = self.exit_bps / 10_000
        return (
            round_step(self._mid_() * (1+entry), self.__market__["tickSize"]),
            round_step(self._mid_() * (1+exit), self.__market__["tickSize"])
        )

    def _buffer_levels_(self, price: float, sens: float=0.1) -> Tuple[float, float]:
        """Upper & lower levels from a given price, acting as a price buffer"""
        buffer = price * (self.entry_bps/10_000) * sens
        return (buffer + price, buffer - price)

    async def _post_limit_bid_(self, price: float, tp: float) -> Union[None, str]:
        """Hardcoded constant params to make core code cleaner, returns orderId"""
        order = await self.__client__.post_create_order(
            symbol=self.symbol,
            side=0,
            type="limit",
            amount=self.qty,
            price=price,
            tp=tp
        )
        return order["return"]["orderId"]

    async def _post_limit_ask_(self, price: float, tp: float) -> Union[None, str]:
        """Hardcoded constant params to make core code cleaner, returns orderId if successful"""
        order = await self.__client__.post_create_order(
            symbol=self.symbol,
            side=1,
            type="limit",
            amount=self.qty,
            price=price,
            tp=tp
        )
        return order["return"]["orderId"]

    async def bid(self) -> None:
        try: 
            entry, exit = self._bid_()
            buffer_lower, buffer_upper = self._buffer_levels_(entry)
            orderId = await self._post_limit_bid_(entry, exit)

            while True:
                await asyncio.sleep(1)

                # Order filled, break loop
                if orderId not in self.__private__["openOrders"]:
                    raise asyncio.CancelledError

                new_entry, new_exit = self._bid_()

                # If entry price leaves bounds, replace...
                if new_entry < buffer_lower or new_entry > buffer_upper:
                    entry, exit = new_entry, new_exit
                    buffer_lower, buffer_upper = self._buffer_levels_(entry)
                    await self.__client__.post_cancel_order(orderId)
                    orderId = await self._post_limit_bid_(entry, exit)

        # If task is cancelled or order filled, break loop
        except asyncio.CancelledError:
            return None

        # Throw any other potential exceptions and move on
        except Exception as e:
            self.logging.error(e)

        finally:
            if orderId in self.__private__["openOrders"]:
                await self.__client__.post_cancel_order(orderId)

            return None

    async def ask(self) -> None:
        try: 
            entry, exit = self._ask_()
            buffer_lower, buffer_upper = self._buffer_levels_(entry)
            orderId = await self._post_limit_ask_(entry, exit)

            while True:
                await asyncio.sleep(1)

                # Order filled, break loop
                if orderId not in self.__private__["openOrders"]:
                    raise asyncio.CancelledError

                new_entry, new_exit = self._ask_()

                # If entry price leaves bounds, replace...
                if new_entry < buffer_lower or new_entry > buffer_upper:
                    entry, exit = new_entry, new_exit
                    buffer_lower, buffer_upper = self._buffer_levels_(entry)
                    await self.__client__.post_cancel_order(orderId)
                    orderId = await self._post_limit_ask_(entry, exit)

        # If task is cancelled or order filled, break loop
        except asyncio.CancelledError:
            return None

        # Throw any other potential exceptions and move on
        except Exception as e:
            self.logging.error(e)

        finally:
            if orderId in self.__private__["openOrders"]:
                await self.__client__.post_cancel_order(orderId)

            return None
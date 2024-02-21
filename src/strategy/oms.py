import asyncio
from typing import List, Tuple, Coroutine, Union
from src.utils.jit_funcs import nbabs
from src.exchanges.bybit.post.order import Order
from src.sharedstate import SharedState

class OMS:
    """
    Manages the order lifecycle for Bybit, including segregating, amending, and placing orders based on strategy needs.

    Attributes
    ----------
    ss : SharedState
        Shared state object to access and update application-wide data.

    Methods
    -------
    segregate_current_orders(orders: Dict) -> Tuple[List, List]:
        Segregates and sorts current orders into buys and sells.
    segregate_new_orders(orders: List) -> Tuple[List, List]:
        Segregates and sorts new orders into buys and sells.
    amend_orders(current_orders: List, new_orders: List) -> Coroutine:
        Amends existing orders based on new order instructions.
    run(new_orders: List) -> Coroutine:
        Orchestrates the order management process, including order segregation, synchronization, and amendment.
    """

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss

    def segregate_current_orders(self) -> Tuple[List, List]:
        buys, sells = [], []
        for orderId, details in self.ss.current_orders.items():
            if details["side"] == "Buy":
                buys.append([orderId, details["side"], details["price"], details["qty"]])
            else:
                sells.append([orderId, details["side"], details["price"], details["qty"]])
        buys.sort(key=lambda x: x[2], reverse=True)
        sells.sort(key=lambda x: x[2])
        return buys, sells

    def segregate_new_orders(self, orders: List) -> Tuple[List, List]:
        buys, sells = [], []
        for order in orders:
            if order[0] == "Buy":
                buys.append(order)
            else:
                sells.append(order)
        buys.sort(key=lambda x: x[1], reverse=True)
        sells.sort(key=lambda x: x[1])
        return buys, sells
    
    def _orders_within_spread_(self, orders: List, spread: float) -> Union[List]:
        within_spread = []
        lower, upper = self.ss.bybit_mid - spread, self.ss.bybit_mid + spread

        for order in orders:
            price = order[1] if isinstance(order[1], float) else order[2]
            if price >= lower and price <= upper:
                within_spread.append(order)
        return within_spread

    def _orders_outside_spread_(self, orders: List, spread: float) -> Union[List]:
        outside_spread = []
        lower, upper = self.ss.bybit_mid - spread, self.ss.bybit_mid + spread

        for order in orders:
            price = order[1] if isinstance(order[1], float) else order[2]
            if price < lower or price > upper:
                outside_spread.append(order)
        return outside_spread

    def _within_bounds_(self, new_delta: float, sensitivity: float = 0.1) -> bool:
        """Truthy whether delta is within min/max limits to change"""
        lower = self.__primary_delta__ * (1 - sensitivity)
        upper = self.__primary_delta__ * (1 + sensitivity)
        return lower < new_delta and upper > new_delta
    
    async def amend_orders(self, current_orders: List, new_orders: List) -> Coroutine:
        tasks = [
            asyncio.create_task(Order(self.ss).amend((current[0], new[1], new[2])))
            for current, new in zip(current_orders, new_orders)
            if nbabs(current[2] - new[1]) > self.ss.buffer
        ]
        return await asyncio.gather(*tasks)

    async def replace_orders(self, to_cancel: List, to_send: List) -> Coroutine:
        ids_to_cancel = [order[0] for order in to_cancel]
        tasks = [Order(self.ss).cancel_batch(ids_to_cancel)]
        tasks.append(Order(self.ss).order_limit_batch(to_send))
        return await asyncio.gather(*tasks)

    async def run(self, new_orders: List[Tuple[str, float, float]], spread: float) -> None:
        """
        Orchestrates the order management process by comparing new orders against current ones,
        determining necessary adjustments, and executing them.

        Steps:
        1. No current orders
            -> Cancel all (for safety), then send new orders

        2. All are bids/asks and have changed (extreme scenario)
            -> Cancel missing and send new in singles

        3. Current and new sides dont match (switching from/to extreme scenario)
            -> Cancel all and send all new

        4. 4 close to BBA orders have changed
            -> Amend changed orders to new price/qty

        5. Outer orders have changed more than buffer
            -> Cancel changed and send changed as batch

        Parameters
        ----------
        new_orders : List[Tuple[str, float, float]]
            A list of new orders, where each order is represented as a tuple of side, price, and quantity.
        """

        # 1st check
        # if not self.ss.current_orders:
        # print("1st check triggered here!")
        await Order(self.ss).cancel_all()
        await Order(self.ss).order_limit_batch(new_orders)
        # print(f"New orders: {self._orders_within_spread_(new_orders, spread)}")
        current_bids, current_asks = self.segregate_current_orders()
        # print(f"Current orders: {self._orders_within_spread_(current_bids + current_asks, spread)}")
        return None

        # Sorting/segregating current & new orders
        current_bids, current_asks = self.segregate_current_orders()
        current_best_bids, current_best_asks = current_bids[:2], current_asks[:2]
        current_outer_bids, current_outer_asks = current_bids[2:], current_asks[2:]

        new_bids, new_asks = self.segregate_new_orders(new_orders)
        new_best_bids, new_best_asks = new_bids[:2], new_asks[:2]
        new_outer_bids, new_outer_asks = new_bids[2:], new_asks[2:]

        # 2nd check
        current_sides_len = len(set(order[1][0] for order in current_bids + current_asks))
        new_sides_len = len(set(order[0] for order in new_orders))

        if (current_sides_len == 1) and (new_sides_len == 1):
            print("2nd check triggered here!")
            current_unique_prices = set(order[2] for order in current_bids + current_asks)
            new_unique_prices = set(order[1] for order in new_orders)
            prices_to_cancel = current_unique_prices - new_unique_prices
            prices_to_send = new_unique_prices - current_unique_prices

            if prices_to_cancel or prices_to_send:
                batches_to_cancel = []
                batches_to_send = []
                for price in prices_to_cancel:
                    batches_to_cancel.append(order[0] for order in current_bids + current_asks if order[2] == price)
                for price in prices_to_send:
                    batches_to_send.append(order for order in new_orders if order[1] == price)
                await self.replace_orders(batches_to_cancel, batches_to_send)

            return None 

        # 3rd check
        if current_sides_len - new_sides_len != 0:
            print("3rd check triggered here!")
            await Order(self.ss).cancel_all()
            await Order(self.ss).order_limit_batch(new_orders)

        # 4th check
        if new_best_bids and new_best_asks:
            print("4th check triggered here!")
            await self.amend_orders(current_best_bids, new_best_bids)
            await self.amend_orders(current_best_asks, new_best_asks)

        # 5th check
        print("5th check triggered here!")
        amend_batches = []

        for current, new in zip(current_outer_bids + current_outer_asks, new_outer_bids + new_outer_asks):
            if nbabs(current[2] - new[1]) > self.ss.buffer:
                amend_batches.append([current[0], new[1], new[2]])

        if amend_batches:
            await Order(self.ss).amend_batch(amend_batches)

        return None
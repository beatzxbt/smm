
import asyncio
from src.utils.jit_funcs import nabs
from src.exchanges.bybit.post.order import Order
from src.sharedstate import SharedState


class Diff:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    def segregate_current_orders(self, orders: dict) -> tuple[list, list]:
        """
        Segregate orders based on their side and sort them by price.
        """

        buys = []
        sells = []

        for orderId, details in orders.items():
            if details["side"] == "Buy":
                buys.append((orderId, (details["side"], details["price"], details["qty"])))

            else:
                sells.append((orderId, (details["side"], details["price"], details["qty"])))

        buys.sort(key=lambda x: x[1][1], reverse=True)
        sells.sort(key=lambda x: x[1][1])

        return buys, sells


    def current_close_to_bba(self) -> tuple[list, list]:
        buys, sells = self.segregate_current_orders(self.ss.current_orders)
        return buys[:2], sells[:2]


    def current_far_from_bba(self, close_bids, close_asks) -> tuple[list, list]:
        close_orders_ids = {order[0] for order in close_bids + close_asks}

        far_orders = {
            orderId: info for orderId, info in self.ss.current_orders.items() 
                    if orderId not in close_orders_ids
        }

        return self.segregate_current_orders(far_orders)


    def current_all(self) -> list:
        cb, ca = self.current_close_to_bba()
        fb, fa = self.current_far_from_bba(cb, ca)
        return cb + ca + fb + fa

    
    def segregate_new_orders(self, orders: list) -> tuple[list, list]:
        """
        Segregate orders based on their side and sort them by price.
        """

        buys = []
        sells = []

        for order in orders:
            if order[0] == "Buy":
                buys.append(order)

            else:
                sells.append(order)

        buys.sort(key=lambda x: x[1], reverse=True)
        sells.sort(key=lambda x: x[1])

        return buys, sells


    def new_close_to_bba(self, new_orders) -> tuple[list, list]:
        buys, sells = self.segregate_new_orders(new_orders)
        return buys[:2], sells[:2]


    def new_far_from_bba(self, new_orders, close_bids, close_asks) -> tuple[list, list]:
        close_to_bba = close_bids + close_asks
        far_from_bba = [order for order in new_orders 
                        if order not in close_to_bba]

        return self.segregate_new_orders(far_from_bba)


    async def amend_orders(self, current_orders, new_orders):
        tasks = [
            asyncio.create_task(Order(self.ss).amend((current[0], new[1], new[2])))
            for current, new in zip(current_orders, new_orders)
            if current[1][1] != new[1]
        ]

        await asyncio.gather(*tasks)


    async def diff(self, new_orders: list) -> bool:
        """
        This function checks new orders vs current orders

        Checks performed:

        - No current orders
            -> Send all orders as batch

        - All are bids/asks and have changed (extreme scenario)
            -> Cancel missing and send new in singles

        - 4 close to BBA orders have changed
            -> Amend changed orders to new price/qty

        - Number of bids/asks have changed for outer orders
            -> Cancel batch and send batch

        - Rest outer orders have changed more than buffer
            -> Cancel changed and send changed as batch
        """

        # First check
        if not self.ss.current_orders:
            await Order(self.ss).order_batch(new_orders)
            return

        # Sorting and segregating orders
        new_best_bids, new_best_asks = self.new_close_to_bba(new_orders)
        new_outer_bids, new_outer_asks = self.new_far_from_bba(new_orders, new_best_bids, new_best_asks)
        new_all_orders = new_orders

        current_best_bids, current_best_asks = self.current_close_to_bba()
        current_outer_bids, current_outer_asks = self.current_far_from_bba(current_best_bids, current_best_asks)
        current_all_orders = self.current_all()

        # Second check
        current_all_sides = set(order[1][0] for order in current_all_orders)
        new_all_sides = set(order[0] for order in new_all_orders)

        # If new and current are both on the same side, amend only
        if len(current_all_sides) == 1 and len(new_all_sides) == 1:
            current_unique_prices = set(order[1][1] for order in current_all_orders)
            new_unique_prices = set(order[1] for order in new_all_orders)
            prices_to_cancel = current_unique_prices - new_unique_prices
            prices_to_send = new_unique_prices - current_unique_prices

            if prices_to_cancel or prices_to_send:
                for prices in prices_to_cancel:
                    orderId = [order[0] for order in current_all_orders if order[1][1] == prices][0]
                    await Order(self.ss).cancel(orderId)

                for prices in prices_to_send:
                    new_order = [order for order in new_all_orders if order[1] == prices][0]
                    await Order(self.ss).order_limit(new_order)    

            return 

        # If swapping to one side first, cancel and order all
        if len(current_all_sides) == 2 and len(new_all_sides) == 1:
            await Order(self.ss).cancel_all()
            await Order(self.ss).order_batch(new_all_orders)

        # Third check
        if new_best_bids and new_best_asks:
            await self.amend_orders(current_best_bids, new_best_bids)
            await self.amend_orders(current_best_asks, new_best_asks)

        # Fourth check
        outer_bids_len_changed = len(current_outer_bids) != len(new_outer_bids)
        outer_asks_len_changed = len(current_outer_asks) != len(new_outer_asks)

        if outer_bids_len_changed or outer_asks_len_changed:
            await Order(self.ss).cancel_all()
            await Order(self.ss).order_batch(new_all_orders)
            return

        # Fifth check
        amend_batches = []

        for current, new in zip(current_outer_bids + current_outer_asks, new_outer_bids + new_outer_asks):
            if nabs(current[1][1] - new[1]) > self.ss.buffer:
                amend_batches.append((current[0], new[1], new[2]))

        if amend_batches:
            await Order(self.ss).amend_batch(amend_batches)
            return

        return

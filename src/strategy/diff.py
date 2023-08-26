
import asyncio
from src.utils.jit_funcs import nabs
from src.exchanges.bybit.order.core import Order
from src.sharedstate import SharedState


class Diff:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate


    async def task(self, func):
        return asyncio.create_task(func)


    def current_close_to_bba(self) -> list:
        
        buys = []
        sells = []

        for order in self.ss.current_orders.items():
            orderId = order[0]
            price = order[1]['price']
            side = order[1]['side']
            qty = order[1]['qty']

            if side == 'Buy':
                buys.append((orderId, [side, price, qty]))

            else:
                sells.append((orderId, [side, price, qty]))

        # Sorting by price, which is the first element of each tuple
        close_bids = sorted(buys, key=lambda x: x[1][1], reverse=True)[:2]
        close_asks = sorted(sells, key=lambda x: x[1][1])[:2]

        return close_bids, close_asks


    def current_far_from_bba(self, close_bids: list, close_asks: list) -> list:
    
        # Grabbing ids of close orders  
        close_orders_ids = [order[0] for order in close_bids + close_asks]  

        # Filter out the close orders and return the orderId with [side, price, qty] info for the remaining orders
        far_orders = [(orderId, info) for orderId, info in self.ss.current_orders.items() if orderId not in close_orders_ids]

        # Separating far orders into bids and asks, and formatting them as lists of orderId with [side, price, qty]
        far_bids = [[orderId, [info['side'], info['price'], info['qty']]] for orderId, info in far_orders if info['side'] == 'Buy']
        far_asks = [[orderId, [info['side'], info['price'], info['qty']]] for orderId, info in far_orders if info['side'] == 'Sell']

        # Sorting bids and asks by price
        far_bids.sort(key=lambda x: x[1][1], reverse=True)
        far_asks.sort(key=lambda x: x[1][1])  

        return far_bids + far_asks

    
    def current_all(self) -> list:
        cb, ca = self.current_close_to_bba()
        return cb + ca + self.current_far_from_bba(cb, ca)


    def new_close_to_bba(self, new_orders: list) -> list:
        return new_orders[:2], new_orders[2:4]

    
    def new_far_from_bba(self, new_orders: list) -> list:
        return new_orders[4:]


    def new_all(self, new_orders: list) -> list:
        return new_orders


    async def diff(self, new_orders: list) -> bool:
        """
        This function checks new orders vs current orders

        Checks performed:
        
        - No current orders
            -> Send all orders as batch

        - Number of new orders and current are not same
            -> Cancel all and send all as batch

        - All are bids/asks and have changed (extreme scenario)
            -> Cancel all and send all as batch

        - 4 close to BBA orders have changed 
            -> Amend changed orders to new price/qty

        - Number of bids/asks have changed for outer orders 
            -> Cancel batch and send batch

        - Rest outer orders have changed more than buffer
            -> Cancel changed and send changed as batch
        """

        # First check performed \
        if self.ss.current_orders is None:
            await Order(self.ss).submit_batch(new_orders)
            return 

        # Sort the new and current orders in a simple format for use \
        new_best_bids, new_best_asks = self.new_close_to_bba(new_orders)
        new_outer_orders = self.new_far_from_bba(new_orders)
        new_outer_bids = sorted([order for order in new_outer_orders if order[0] == 'Buy'], key=lambda x: x[1])
        new_outer_asks = sorted([order for order in new_outer_orders if order[0] == 'Sell'], key=lambda x: x[1])
        new_all_orders = self.new_all(new_orders)

        current_best_bids, current_best_asks = self.current_close_to_bba()
        current_outer_orders = self.current_far_from_bba(current_best_bids, current_best_asks)
        current_outer_bids = sorted([order for order in current_outer_orders if order[1][0] == 'Buy'], key=lambda x: x[1][1]) 
        current_outer_asks = sorted([order for order in current_outer_orders if order[1][0] == 'Sell'], key=lambda x: x[1][1])
        current_all_orders = self.current_all() 

        # Second check performed \
        if len(self.ss.current_orders) < len(new_orders):
            await Order(self.ss).cancel_all()
            await Order(self.ss).submit_batch(new_orders)
            return 

        # Third check performed \
        if len(current_outer_bids) == len(current_outer_orders) or len(current_outer_asks) == len(current_outer_orders):

            if new_all_orders != current_all_orders:
                await Order(self.ss).cancel_all()
                await Order(self.ss).submit_batch(new_orders)

            return 

        # Fourth check performed \
        if len(new_best_bids) > 0 and len(new_best_asks) > 0:
            
            tasks = []

            # Check the prices of first 2 bids, and amend if changes to price \
            for i, new in enumerate(new_best_bids):
                old_order = current_best_bids[i]
                old_price = old_order[1][1]

                new_price  = new[1]
                new_qty = new[2]

                if new_price != old_price:
                    orderId = old_order[0]
                    price = new_price
                    qty = new_qty

                    tasks.append(self.task(Order(self.ss).amend((orderId, price, qty))))

            # Check the prices of first 2 asks, and amend if changes to price \
            for i, new in enumerate(new_best_asks):
                old_order = current_best_asks[i]
                old_price = old_order[1][1]

                new_price  = new[1]
                new_qty = new[2]

                if new_price != old_price:
                    orderId = old_order[0]
                    price = new_price
                    qty = new_qty

                    tasks.append(self.task(Order(self.ss).amend((orderId, price, qty))))

            await asyncio.gather(*tasks)

        # Fifth check performed \
        if len(current_outer_bids) != len(new_outer_bids) or len(current_outer_asks) != len(new_outer_asks):

            # Grabbing ids of current outer orders to cancel
            current_outer_orders_ids = [order[0] for order in current_outer_orders]
            
            # Cancel current outer orders and submit new outer orders
            await Order(self.ss).cancel_batch(current_outer_orders_ids)
            await Order(self.ss).submit_batch(new_outer_orders)
            return

        # Sixth check performed \
        amend_batches = []

        # Check if new prices are within certain range of current prices
        for current, new in zip(current_outer_bids, new_outer_bids):
            if nabs(current[1][1] - new[1]) > self.ss.buffer:
                amend_batches.append((current[0], new[1], new[2]))

        for current, new in zip(current_outer_asks, new_outer_asks):
            if nabs(current[1][1] - new[1]) > self.ss.buffer:
                amend_batches.append((current[0], new[1], new[2]))

        # If there are any amendments, execute them
        if amend_batches:
            await Order(self.ss).amend_batch(amend_batches)

        return

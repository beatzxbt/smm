import asyncio
import json

from src.bybit.order.core import Order



class OrderStrategies:


    def __init__(self, sharedstate):

        self.ss = sharedstate
        self.symbol = self.ss.bybit_symbol


    async def limit_chase(self, side: str, qty) -> json:

        curr_orderId = None
        
        # Chasing bid \
        if side == 'Buy':

            try: 
                best_bid = self.ss.bybit_bba[0][0]

                init_order_tuple = (side, best_bid, qty)
                init_order = await Order(self.ss).submit_limit(init_order_tuple)

                # Init order ID, will be used to amend the order \
                curr_orderId = init_order['orderId']

                while True:

                    # Chase every 100ms \
                    await asyncio.sleep(0.1)

                    # Updated bid price \
                    new_best_bid = self.ss.bybit_bba[0][0]

                    # If best bid price has increased, amend order to new best bid \
                    if best_bid < new_best_bid:
                        
                        # Updated price and qty \
                        best_bid = new_best_bid
                        amend_order_tuple = (curr_orderId, best_bid, qty)
                        amend_order = await Order(self.ss).amend(amend_order_tuple)

                    # Watch execution feed for order fill \
                    if len(self.ss.futures_execution_feed) != 0:

                        lastest_fill = self.ss.futures_execution_feed[-1]

                        if lastest_fill['orderId'] == curr_orderId:
                            return lastest_fill

            # If this task is cancelled, cancel the order \
            except asyncio.CancelledError:

                if curr_orderId is not None:
                    await Order(self.ss).cancel(curr_orderId)
                    print(f"Chase cancelled, {curr_orderId} cancelled")
                    
                raise 

            # Handle any other potential exceptions \
            except Exception as e:
                print(e)
                raise


        if side == 'Sell':
            
            try: 
                best_ask = self.ss.bybit_bba[1][0]

                init_order_tuple = (side, best_ask, qty)
                init_order = await Order(self.ss).submit_limit(init_order_tuple)

                # Init order ID, will be used to amend the order \
                curr_orderId = init_order['orderId']

                while True:

                    # Chase every 100ms \
                    await asyncio.sleep(0.1)

                    # Updated ask price \
                    new_best_ask = self.ss.bybit_bba[1][0]

                    # If best ask price has increased, amend order to new best ask \
                    if best_ask > new_best_ask:
                        
                        # Updated price and qty \
                        best_ask = new_best_ask
                        amend_order_tuple = (curr_orderId, best_ask, qty)
                        amend_order = await Order(self.ss).amend(amend_order_tuple)

                    # Watch execution feed for order fill \
                    if len(self.ss.futures_execution_feed) != 0:

                        lastest_fill = self.ss.futures_execution_feed[-1]

                        if lastest_fill['orderId'] == curr_orderId:
                            return lastest_fill

            # If this task is cancelled, cancel the order \
            except asyncio.CancelledError:

                if curr_orderId is not None:
                    await Order(self.ss).cancel(curr_orderId)
                    print(f"Chase cancelled, {curr_orderId} cancelled")
                    
                raise 

            # Handle any other potential exceptions \
            except Exception as e:
                print(e)
                raise

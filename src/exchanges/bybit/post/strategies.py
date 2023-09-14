
import asyncio
from src.exchanges.bybit.post.order import Order
from src.sharedstate import SharedState


class OrderStrategies:


    def __init__(self, sharedstate: SharedState):
        self.ss = sharedstate
        self.symbol = self.ss.bybit_symbol


    async def limit_chase(self, side: str, qty) -> dict | None:
        
        # Invalid side check 
        assert side in ["Buy", "Sell"], "Invalid side provided"

        if side == "Buy":
            best_price_index = 0
            comparison_operator = (lambda old, new: old < new)

        else:
            best_price_index = 1
            comparison_operator = (lambda old, new: old > new)

        try:
            curr_orderId = None # Handles bad orderId if latency high
            best_price = self.ss.bybit_bba[best_price_index][0]
            init_order_tuple = (side, best_price, qty)
            init_order = await Order(self.ss).order_limit(init_order_tuple)
            curr_orderId = init_order["orderId"]

            while True:
                new_best_price = self.ss.bybit_bba[best_price_index][0]

                if comparison_operator(best_price, new_best_price):
                    best_price = new_best_price
                    amend_order_tuple = (curr_orderId, best_price, qty)
                    await Order(self.ss).amend(amend_order_tuple)

                if self.ss.execution_feed:
                    latest_fill = self.ss.execution_feed[-1]
                    if latest_fill["orderId"] == curr_orderId:
                        return latest_fill

                # Chase every 100ms
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            if curr_orderId is not None:
                await Order(self.ss).cancel(curr_orderId)
                print(f"Chase aborted, {curr_orderId} cancelled")

            raise

        except Exception as e:
            print(e)
            raise
        
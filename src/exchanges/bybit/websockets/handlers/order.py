
from src.sharedstate import SharedState


class BybitOrderHandler:


    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate

    
    def sync(self, recv: dict) -> None:

        data = recv["result"]["list"]

        self.ss.current_orders = {
            o["orderId"]: {"price": float(o["price"]), "qty": float(o["qty"]), "side": o["side"]} 
            for o in data
        }

    def process(self, data: dict) -> None:

        new_orders = {
            order["orderId"]: {"price": order["price"], "qty": order["qty"], "side": order["side"]}
            for order in data
            if order.get("orderStatus") == "New"
        }

        filled_orders = set(
            order["orderId"] 
            for order in data 
            if order["orderStatus"] == "Filled"
        )

        # Update the orders
        self.ss.current_orders.update(new_orders)

        # Remove filled orders
        for order_id in filled_orders:
            self.ss.current_orders.pop(order_id, None)

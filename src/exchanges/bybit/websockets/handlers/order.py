from typing import Dict
from src.sharedstate import SharedState


class BybitOrderHandler:
    _opened_ = ["New", "PartiallyFilled"]
    _closed_ = ["Rejected", "Filled", "Cancelled"]

    def __init__(self, ss: SharedState) -> None:
        self.ss = ss

    def sync(self, recv: Dict) -> None:
        self.ss.current_orders = {
            order["orderId"]: {"side": order["side"], "price": float(order["price"]), "qty": float(order["qty"])} 
            for order in recv["result"]["list"]
        }

    def process(self, data: Dict) -> None:
        new_orders = {
            order["orderId"]: {"side": order["side"], "price": float(order["price"]), "qty": float(order["qty"])}
            for order in data
            if order["orderStatus"] in self._opened_
        }

        filled_orders = set(
            order["orderId"] 
            for order in data 
            if order["orderStatus"] in self._closed_
        )

        # Update the orders
        self.ss.current_orders.update(new_orders)

        # Remove filled orders
        for order_id in filled_orders:
            self.ss.current_orders.pop(order_id, None)
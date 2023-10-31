
from frameworks.sharedstate.private import PrivateDataSharedState


class BybitOrderHandler:


    def __init__(self, sharedstate: PrivateDataSharedState, symbol: str) -> None:
        self.pdss = sharedstate
        self.symbol = symbol
        self.bybit = self.pdss.bybit[self.symbol]["Data"]

    
    def sync(self, recv: list) -> None:
        self.bybit["current_orders"] = {
            order["orderId"]: {"price": float(order["price"]), "qty": float(order["qty"]), "side": order["side"]} 
            for order in recv["result"]["list"]
        }


    def update(self, data: dict) -> None:
        new_orders = {
            order["orderId"]: {"price": float(order["price"]), "qty": float(order["qty"]), "side": order["side"]}
            for order in data
            if order["orderStatus"] == "New" and order["symbol"] == self.symbol
        }

        filled_orders = set(
            order["orderId"] 
            for order in data 
            if order["orderStatus"] == "Filled" and order["symbol"] == self.symbol
        )

        # Update the orders
        self.bybit["current_orders"].update(new_orders)

        # Remove filled orders
        for order_id in filled_orders:
            self.bybit["current_orders"].pop(order_id, None)

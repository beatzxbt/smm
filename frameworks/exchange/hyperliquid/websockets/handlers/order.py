
from frameworks.sharedstate.private import PrivateDataSharedState


class HyperLiquidOrderHandler:


    def __init__(self, sharedstate: PrivateDataSharedState, symbol: str) -> None:
        self.pdss = sharedstate
        self.symbol = symbol
        self.hlq = self.pdss.hyperliquid[self.symbol]["Data"]

    
    def sync(self, recv: list) -> None:
        self.hlq["current_orders"] = {
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
        self.hlq["current_orders"].update(new_orders)

        # Remove filled orders
        for order_id in filled_orders:
            self.hlq["current_orders"].pop(order_id, None)

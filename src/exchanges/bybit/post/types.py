from typing import Dict

class BybitFormats:
    category = "linear"

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self._base_ = {
            "category": self.category,
            "symbol": self.symbol,
        }

    def create_limit(self, side: str, price: str, qty: str) -> Dict:
        return {
            **self._base_,
            "side": side,
            "orderType": "Limit",
            "price": price,
            "qty": qty,
            "timeInForce": "PostOnly",
        }

    def create_market(self, side: str, qty: str) -> Dict:
        return {
            **self._base_,
            "side": side,
            "orderType": "Market",
            "qty": qty,
        }

    def create_amend(self, orderId: str, price: str, qty: str) -> Dict:
        return {
            **self._base_, 
            "orderId": orderId, 
            "price": price, 
            "qty": qty
        }
    
    def create_cancel(self, orderId: str) -> Dict:
        return {
            **self._base_, 
            "orderId": orderId
        }
    
    def create_cancel_all(self) -> Dict:
        return self._base_

from enum import Enum
from typing import Union


class OrderCategory(Enum):
    SPOT = "spot"
    LINEAR = "linear"


class OrderBase:


    def __init__(self, symbol: str, category: OrderCategory) -> None:
        self.symbol = symbol
        self.category = category.value


    def _base_payload(self) -> dict:
        return {
            "category": self.category,
            "symbol": self.symbol,
        }


    def create_limit_payload(self, side: str, price: str, qty: str, tp: str) -> dict:
        limit = {
            **self._base_payload(),
            "side": side,
            "orderType": "Limit",
            "price": price,
            "qty": qty,
            "timeInForce": "PostOnly",
        }

        if tp is not None:
            limit["takeProfit"] = str(tp)
            limit["tpslMode"] = "Partial"
            limit["tpLimitPrice"] = str(tp)
            limit["tpOrderType"] = "Limit"

        return limit


    def create_market_payload(self, side: str, qty: str, tp: str) -> dict:
        market = {
            **self._base_payload(),
            "side": side,
            "orderType": "Market",
            "qty": qty,
        }

        if tp is not None:
            market["takeProfit"] = str(tp)
            market["tpslMode"] = "Partial"
            market["tpLimitPrice"] = str(tp)
            market["tpOrderType"] = "Limit"

        return market


    def create_cancel_payload(self, orderId: str) -> dict:
        return {
            **self._base_payload(), 
            "orderId": orderId
        }


    def create_amend_payload(self, orderId: str, price: str, qty: str, tp: str) -> dict:
        amend = {
                **self._base_payload(), 
                "orderId": orderId, 
                "price": price,
                "qty": qty
            }

        if tp is not None:
            amend["takeProfit"] = str(tp)
            amend["tpLimitPrice"] = str(tp)
            
        return amend



class OrderTypesSpot(OrderBase):

    # Needs work #
    
    def __init__(self, symbol: str, margin: bool) -> None:
        super().__init__(symbol, OrderCategory.SPOT)
        self.is_leverage = 1 if margin else 0


    def _base_payload(self) -> dict[str, Union[str, int]]:
        payload = super()._base_payload()
        payload["isLeverage"] = self.is_leverage
        return payload



class OrderTypesFutures(OrderBase):


    def __init__(self, symbol: str):
        super().__init__(symbol, OrderCategory.LINEAR)


    def limit(self, order, tp):
        return self.create_limit_payload(order[0], order[1], order[2], tp)


    def market(self, order, tp):
        return self.create_market_payload(order[0], order[1], tp)


    def amend(self, order, tp):
        return self.create_amend_payload(order[0], order[1], order[2], tp)


    def cancel(self, orderId):
        return self.create_cancel_payload(orderId)


    def cancel_all(self):
        return self._base_payload()

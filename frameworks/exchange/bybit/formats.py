from typing import Dict, Optional
from frameworks.tools.logging import time_ms
from frameworks.exchange.bybit.types import BybitOrderSides, BybitOrderTypes


class BybitFormats:
    def __init__(self) -> None:
        self.convert_side = BybitOrderSides
        self.convert_type = BybitOrderTypes
        self.base_payload = {"category": "linear"}

    def create_order(
        self,
        symbol: str,
        side: float,
        orderType: float,
        size: float,
        price: Optional[float],
    ) -> Dict:
        format = {
            **self.base_payload,
            "symbol": symbol,
            "side": self.convert_side.to_side(side),
            "orderType": self.convert_type.to_type(orderType),
            "qty": str(size)
        }
        
        # Market order
        if orderType == 1:
            return format
        
        # Limit order
        elif orderType == 0:
            format["price"] = str(price)
            format["timeInForce"] = "PostOnly"

        return format
    
    def amend_order(
        self,
        orderId: str,
        size: float,
        price: float,
    ) -> Dict:
        format = {
            **self.base_payload,
            "orderId": orderId,
            "price": str(price),
            "qty": str(size)
        }

        return format
    
    def cancel_order(self, orderId: str) -> Dict:
        format = {
            **self.base_payload, 
            "orderId": orderId
        }

        return format

    def cancel_all_orders(self, symbol: str) -> Dict:
        format = {
            **self.base_payload, 
            "symbol": symbol
        }

        return format

    def get_ohlcv(self, symbol: str, interval: int) -> Dict:
        format = {
            **self.base_payload,
            "symbol": symbol,
            "interval": str(interval),
            "limit": "1000",  # NOTE: [1, 1000]. Default: 200
        }

        return format

    def get_trades(self, symbol: str) -> Dict:
        return {
            **self.base_payload,
            "symbol": symbol,
            "limit": "1000",  # NOTE: [1,1000], default: 500
        }

    def get_orderbook(self, symbol: str) -> Dict:
        return {
            **self.base_payload,
            "symbol": symbol,
            "limit": "200",  # NOTE: [1, 200]. Default: 25
        }

    def instrument(self, symbol: str) -> Dict:
        format = {
            **self.base_payload, 
            "symbol": symbol
        }

        return format

    def open_orders(self, symbol: str) -> Dict:
        format = {
            **self.base_payload, 
            "symbol": symbol
        }

        return format

    def current_position(self, symbol: str) -> Dict:
        format = {
            **self.base_payload, 
            "symbol": symbol
        }

        return format

    def account_info(self) -> Dict:
        return self.base_payload

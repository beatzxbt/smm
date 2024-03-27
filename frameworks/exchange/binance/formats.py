from typing import Dict, Optional
from frameworks.tools.logging import time_ms
from frameworks.exchange.binance.types import BinanceOrderSides, BinanceOrderTypes

class BinanceFormats:
    def __init__(self) -> None:
        self.convert_side = BinanceOrderSides
        self.convert_type = BinanceOrderTypes

    def create_order(
        self,
        symbol: str,
        side: float,
        type: float,
        size: float,
        price: Optional[float],
    ) -> Dict:
        format = {
            "symbol": symbol,
            "side": self.convert_side.to_side(side),
            "type": self.convert_type.to_type(type),
            "quantity": str(size),
            "timestamp": time_ms()
        }
        
        # Market order
        if type == 1:
            return format
        
        # Limit order
        elif type == 0:
            format["price"] = str(price)
            format["timeInForce"] = "PostOnly"

        return format

    def amend_order(
        self,
        orderId: str,
        symbol: str, 
        side: float, 
        size: float,
        price: float,
    ) -> Dict:
        format = {
            "orderId": orderId,
            "symbol": symbol,
            "side": self.convert_side.to_side(side),
            "quantity": str(size),
            "price": str(price),
            "timestamp": time_ms()
        }

        return format

    def cancel_order(self, symbol: str, orderId: str) -> Dict:
        format = {
            "symbol": symbol,
            "orderId": orderId,
            "timestamp": time_ms()
        }

        return format

    def cancel_all_orders(self, symbol: str) -> Dict:
        format = {
            "symbol": symbol,
            "timestamp": time_ms()
        }

        return format

    def get_ohlcv(self, symbol: str, interval: int, limit: int) -> Dict:
        format = {
            "symbol": symbol,
            "interval": str(interval),
            "limit": limit,  # NOTE: [1, 1000]. Default: 200
        }

        return format

    def get_trades(self, symbol: str, limit: int) -> Dict:
        format = {
            "symbol": symbol,
            "limit": limit
        }

        return format

    def get_orderbook(self, symbol: str, limit: int) -> Dict:
        format = {
            "symbol": symbol,
            "limit": limit
        }

        return format

    def get_open_orders(self, symbol: str) -> Dict:
        format =  {
            "symbol": symbol,
            "timestamp": time_ms()
        }

        return format

    def get_open_position(self, symbol: str) -> Dict:
        format =  {
            "symbol": symbol,
            "timestamp": time_ms()
        }

        return format

    def get_listen_key(self) -> Dict:
        return {}
    
    def get_exchange_info(self) -> Dict:
        return {}
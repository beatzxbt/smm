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
        side: int,
        orderType: int,
        size: float,
        price: Optional[float],
    ) -> Dict:
        format = {
            "symbol": symbol,
            "side": self.convert_side.to_str(side),
            "type": self.convert_type.to_str(orderType),
            "quantity": str(size),
            "timestamp": str(time_ms()),
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
        symbol: str,
        side: int,
        size: float,
        price: float,
    ) -> Dict:
        format = {
            "orderId": orderId,
            "symbol": symbol,
            "side": self.convert_side.to_str(side),
            "quantity": str(size),
            "price": str(price),
            "timestamp": str(time_ms()),
        }

        return format

    def cancel_order(self, symbol: str, orderId: str) -> Dict:
        format = {"symbol": symbol, "orderId": orderId, "timestamp": str(time_ms())}

        return format

    def cancel_all_orders(self, symbol: str) -> Dict:
        format = {"symbol": symbol, "timestamp": str(time_ms())}

        return format

    def get_ohlcv(self, symbol: str, interval: str, limit: int) -> str:
        format = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        return format

    def get_trades(self, symbol: str, limit: int) -> str:
        format = {"symbol": symbol, "limit": limit}

        return format

    def get_orderbook(self, symbol: str, limit: int) -> str:
        format = {"symbol": symbol, "limit": limit}

        return format

    def get_ticker(self, symbol: str) -> str:
        format = {"symbol": symbol}

        return format

    def get_open_orders(self, symbol: str) -> str:
        format = {"symbol": symbol, "timestamp": str(time_ms())}

        return format

    def get_open_position(self, symbol: str) -> str:
        format = {"symbol": symbol, "timestamp": str(time_ms())}

        return format

    def get_exchange_info(self) -> str:
        return {}

    def get_listen_key(self) -> str:
        return {}

    def ping_listen_key(self) -> Dict:
        return {}

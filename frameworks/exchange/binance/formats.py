from typing import Dict, Optional, Union

from frameworks.tools.logging import time_ms
from frameworks.exchange.base.formats import Formats
from frameworks.exchange.binance.types import BinanceOrderSides, BinanceOrderTypes


class BinanceFormats(Formats):
    def __init__(self) -> None:
        super().__init__(BinanceOrderSides, BinanceOrderTypes)

    async def create_order(
        self,
        symbol: str,
        side: Union[int, float],
        orderType: Union[int, float],
        size: float,
        price: Optional[float] = None,
        orderId: Optional[Union[str, int]] = None,
    ) -> Dict:
        format = {
            "symbol": symbol,
            "side": self.convert_side.to_str(side),
            "type": self.convert_order_type.to_str(orderType),
            "quantity": str(size),
            "timestamp": str(time_ms()),
        }

        if orderType == 1:
            return format

        if orderType == 0:
            format["price"] = str(price)
            format["timeInForce"] = "GTX"

        return format

    async def amend_order(
        self,
        symbol: str,
        orderId: Union[str, int],
        side: Union[int, float],
        size: float,
        price: float,
    ) -> Dict:
        return {
            "orderId": orderId,
            "symbol": symbol,
            "side": self.convert_side.to_str(side),
            "quantity": str(size),
            "price": str(price),
            "timestamp": str(time_ms()),
        }

    async def cancel_order(self, symbol: str, orderId: Union[str, int]) -> Dict:
        return {"symbol": symbol, "orderId": orderId, "timestamp": str(time_ms())}

    async def cancel_all_orders(self, symbol: str) -> Dict:
        return {"symbol": symbol, "timestamp": str(time_ms())}

    async def get_ohlcv(self, symbol: str, interval: Union[int, str]) -> Dict:
        return {"symbol": symbol, "interval": interval, "limit": "1000"}

    async def get_trades(self, symbol: str) -> Dict:
        return {"symbol": symbol, "limit": "1000"}

    async def get_orderbook(self, symbol: str) -> Dict:
        return {"symbol": symbol, "limit": "100"}

    async def get_ticker(self, symbol: str) -> Dict:
        return {"symbol": symbol}

    async def get_open_orders(self, symbol: str) -> Dict:
        return {"symbol": symbol, "timestamp": str(time_ms())}

    async def get_position(self, symbol: str) -> Dict:
        return {"symbol": symbol, "timestamp": str(time_ms())}

    async def get_account_info(self) -> Dict:
        return {"timestamp": str(time_ms())}

    async def get_exchange_info(self) -> Dict:
        return {}

    async def get_listen_key(self) -> Dict:
        return {}

    async def ping_listen_key(self) -> Dict:
        return {}

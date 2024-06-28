from typing import List, Dict

from frameworks.tools.logging import time_ms
from frameworks.exchange.base.types import Order, OrderType
from frameworks.exchange.base.formats import Formats
from frameworks.exchange.binance.types import BinanceSideConverter, BinanceOrderTypeConverter, BinanceTimeInForceConverter, BinancePositionDirectionConverter


class BinanceFormats(Formats):
    def __init__(self) -> None:
        super().__init__(
            convert_side=BinanceSideConverter(),
            convert_order_type=BinanceOrderTypeConverter(),
            convert_time_in_force=BinanceTimeInForceConverter(),
            convert_position_direction=BinancePositionDirectionConverter()
        )
        self.base_payload = {"recvWindow": str(self.recvWindow)}

    def create_order(
        self,
        order
    ) -> Dict:
        format = {
            **self.base_payload,
            "symbol": order.symbol,
            "side": self.convert_side.to_str(order.side),
            "type": self.convert_order_type.to_str(order.orderType),
            "timeInForce": self.convert_tif.to_str(order.timeInForce),
            "quantity": str(order.size),
            **({"newClientOrderId": order.clientOrderId} if order.clientOrderId else {}),
            "timestamp": str(time_ms()),
        }

        match order.orderType:
            case OrderType.MARKET:
                return format

            case OrderType.LIMIT:
                format["price"] = str(order.price)

        return format
    
    def batch_create_orders(
        self,
        orders: List[Order]
    ) -> Dict:
        batched_orders = []

        for order in orders:
            single_order = self.create_order(order)
            del single_order["recvWindow"]
            del single_order["timestamp"]
            batched_orders.append(order)

        return {
            "batchOrders": batched_orders,
            **self.base_payload,
            "timestamp": str(time_ms()),
        }
    
    def amend_order(
        self,
        order
    ) -> Dict:
        return {
            **self.base_payload,
            **({"orderId": order.orderId} if order.orderId else {}),
            **({"origClientOrderId": order.clientOrderId} if order.clientOrderId else {}),
            "symbol": order.symbol,
            "side": self.convert_side.to_str(order.side),
            "quantity": str(order.size),
            "price": str(order.price),
            "timestamp": str(time_ms())
        }

    def batch_amend_orders(self, orders: List[Order]) -> Dict:
        batched_amends = []

        for order in orders:
            single_amend = self.amend_order(order)
            del single_amend["recvWindow"]
            del single_amend["timestamp"]
            batched_amends.append(order)
    
        return {
            "batchOrders": batched_amends,
            **self.base_payload,
            "timestamp": str(time_ms()),
        }
    
    def cancel_order(self, order) -> Dict:
        return {
            **self.base_payload,
            "symbol": order.symbol, 
            **({"orderId": order.orderId} if order.orderId else {}),
            **({"origClientOrderId": order.clientOrderId} if order.clientOrderId else {}),
            "timestamp": str(time_ms())
        }

    def batch_cancel_orders(self, orders: List[Order]) -> Dict:
        return {
            "symbol": orders[0].symbol, # TODO: Find a better solution for this!
            "orderIdList": [order.orderId for order in orders if order.orderId is not None],
            "origClientOrderIdList": [order.clientOrderId for order in orders if order.clientOrderId is not None],
            **self.base_payload,
            "timestamp": str(time_ms()),
        }
    
    def cancel_all_orders(self, symbol: str) -> Dict:
        return {
            **self.base_payload,
            "symbol": symbol, 
            "timestamp": str(time_ms())
        }

    def get_ohlcv(self, symbol, interval) -> Dict:
        return {"symbol": symbol, "interval": interval, "limit": "1000"}

    def get_trades(self, symbol) -> Dict:
        return {"symbol": symbol, "limit": "1000"}

    def get_orderbook(self, symbol) -> Dict:
        return {"symbol": symbol, "limit": "100"}

    def get_ticker(self, symbol) -> Dict:
        return {"symbol": symbol}

    def get_open_orders(self, symbol) -> Dict:
        return {"symbol": symbol, "timestamp": str(time_ms())}

    def get_position(self, symbol) -> Dict:
        return {"symbol": symbol, "timestamp": str(time_ms())}

    def get_account_info(self) -> Dict:
        return {"timestamp": str(time_ms())}

    def get_exchange_info(self) -> Dict:
        return {}

    def get_listen_key(self) -> Dict:
        return {}

    def ping_listen_key(self) -> Dict:
        return {}

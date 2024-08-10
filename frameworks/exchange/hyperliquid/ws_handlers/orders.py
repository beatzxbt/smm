from typing import List, Dict, Any

from frameworks.exchange.base.ws_handlers.orders import Order, Orders, OrdersHandler
from frameworks.exchange.base.constants import OrderType, TimeInForce
from frameworks.exchange.hyperliquid.types import (
    HyperliquidSideConverter,
    HyperliquidOrderTypeConverter,
    HyperliquidTimeInForceConverter,
)

class HyperliquidOrdersHandler(OrdersHandler):
    _overwrite_ = {"open"}
    _remove_ = {"filled", "canceled", "triggered", "rejected", "marginCanceled"}

    def __init__(self, orders: Orders, symbol: str) -> None:
        super().__init__(orders)
        self.symbol = symbol

        self.side_converter = HyperliquidSideConverter()
        self.order_type_converter = HyperliquidOrderTypeConverter()
        self.tif_converter = HyperliquidTimeInForceConverter()
    
    def refresh(self, recv: Dict[str, Any]) -> None:
        try:
            for order in recv["list"]:
                if order["symbol"] != self.symbol:
                    continue

                new_order = Order(
                    symbol=self.symbol,
                    side=self.side_converter.to_num(order.get("side")),
                    orderType=self.order_type_converter.to_num(order.get("origType")),
                    timeInForce=self.tif_converter.to_num(order.get("timeInForce")),
                    price=float(order.get("price")),
                    size=float(order.get("qty")) - float(order.get("leavesQty")),
                    orderId=order.get("orderId"),
                    clientOrderId=order.get("orderLinkId"),
                )

                self.orders[new_order.orderId] = new_order

        except Exception as e:
            raise Exception(f"Orders refresh - {e}")
        
    def process(self, recv: Dict) -> None:
        try:
            data: Dict[str, Any] = recv["order"]
            order_status: str = recv["status"]

            if data["coin"] != self.symbol:
                return None

            if order_status in self._overwrite_:
                new_order = Order(
                    symbol=self.symbol,
                    side=self.side_converter.to_num(data.get("side")),
                    orderType=OrderType.LIMIT, # Not provided, assumed LIMIT order
                    timeInForce=None, # Not provided
                    price=float(data.get("limitPx")),
                    size=float(data.get("origSz")) - float(data.get("sz")),
                    orderId=data.get("oid"),
                    clientOrderId=data.get("cloid"),
                )

                self.orders[new_order.orderId] = new_order

            elif order_status in self._remove_:
                del self.orders[data["oid"]]

        except Exception as e:
            raise Exception(f"Orders refresh - {e}")
        
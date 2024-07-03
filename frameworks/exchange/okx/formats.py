from typing import Dict, List, Tuple, Union
from frameworks.exchange.okx.types import OkxSideConverter, OkxOrderTypeConverter
from frameworks.exchange.base.formats import Formats


class OkxFormats(Formats):
    def __init__(self) -> None:
        super().__init__(OkxSideConverter, OkxOrderTypeConverter)
        self.base_payload = {}

    def create_order(
        self,
        symbol: str,
        side: str,
        orderType: str,
        size: float,
        price: float,
        clientOrderId: str = None
    ) -> Dict:
        order = {
            "instId": symbol,
            "tdMode": "cross",  # Assuming cross margin mode
            "side": self.convert_side.to_str(side),
            "ordType": self.convert_order_type.to_str(orderType),
            "sz": str(size),
        }

        if clientOrderId:
            order["clOrdId"] = clientOrderId

        if orderType == "limit":
            order["px"] = str(price)

        return order

    def batch_create_orders(
        self,
        symbol: str,
        sides: List[str],
        orderTypes: List[str],
        sizes: List[float],
        prices: List[float],
        clientOrderIds: List[str]
    ) -> Dict:
        orders = []

        for side, orderType, size, price, clientOrderId in zip(sides, orderTypes, sizes, prices, clientOrderIds):
            order = self.create_order(
                symbol, side, orderType, size, price, clientOrderId
            )
            orders.append(order)

        return {"batch": orders}

    def amend_order(
        self,
        symbol: str,
        orderId: str = None,
        clientOrderId: str = None,
        size: float = None,
        price: float = None,
    ) -> Dict:
        order = {"instId": symbol}

        if orderId:
            order["ordId"] = orderId

        if clientOrderId:
            order["clOrdId"] = clientOrderId

        if size:
            order["newSz"] = str(size)

        if price:
            order["newPx"] = str(price)

        return order

    def batch_amend_orders(
        self,
        symbol: str,
        orderIds: List[str],
        clientOrderIds: List[str],
        sizes: List[float],
        prices: List[float]
    ) -> Dict:
        orders = []

        for orderId, clientOrderId, size, price in zip(orderIds, clientOrderIds, sizes, prices):
            order = self.amend_order(
                symbol, orderId, clientOrderId, size, price
            )
            orders.append(order)

        return {"batch": orders}

    def cancel_order(self, symbol: str, orderId: str = None, clientOrderId: str = None) -> Dict:
        order = {"instId": symbol}

        if orderId:
            order["ordId"] = orderId

        if clientOrderId:
            order["clOrdId"] = clientOrderId

        return order

    def batch_cancel_orders(self, symbol: str, orderIds: List[str], clientOrderIds: List[str]) -> Dict:
        orders = []

        for orderId, clientOrderId in zip(orderIds, clientOrderIds):
            order = self.cancel_order(symbol, orderId, clientOrderId)
            orders.append(order)

        return {"batch": orders}

    def cancel_all_orders(self, symbol: str) -> Dict:
        return {"instId": symbol}

    def get_ohlcv(self, symbol: str, interval: str) -> Dict:
        return {
            "instId": symbol,
            "bar": interval,
        }

    def get_trades(self, symbol: str) -> Dict:
        return {
            "instId": symbol,
            "limit": "100",  # NOTE: [1,100], default: 100
        }

    def get_orderbook(self, symbol: str, limit: int = 200) -> Dict:
        return {
            "instId": symbol,
            "sz": str(limit),  # NOTE: [1, 400]. Default: 25
        }

    def get_ticker(self, symbol: str) -> Dict:
        return {"instId": symbol}

    def get_open_orders(self, symbol: str) -> Dict:
        return {"instId": symbol}

    def get_position(self, symbol: str) -> Dict:
        return {"instId": symbol}

    def get_account_info(self) -> Dict:
        return {}

    def get_instrument_info(self, symbol: str) -> Dict:
        return {"instId": symbol}
    
    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        return {
            "instId": symbol, 
            "lever": leverage
        }

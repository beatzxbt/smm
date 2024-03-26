from typing import Dict, Optional


class BybitFormats:
    def __init__(self) -> None:
        self._base_payload_ = {"category": self.category}

    def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Dict:
        format = {
            **self._base_payload_,
            "symbol": symbol,
            "side": side,
            "orderType": type,
            "price": price,
            "qty": amount,
        }

        if price is not None:
            format["timeInForce"] = "PostOnly"

        if tp is not None:
            str_tp = str(tp)
            format["takeProfit"] = str_tp
            format["tpslMode"] = "Partial"
            format["tpLimitPrice"] = str_tp
            format["tpOrderType"] = "Limit"

        return format

    def amend_order(
        self,
        orderId: str,
        amount: float,
        price: float,
        tp: Optional[float] = None,
    ) -> Dict:
        format = {
            **self._base_payload_,
            "orderId": orderId,
            "price": str(price),
            "qty": str(amount),
        }

        if tp is not None:
            str_tp = str(tp)
            format["takeProfit"] = str_tp
            format["tpLimitPrice"] = str_tp

        return format

    def cancel_order(self, orderId: str) -> Dict:
        return {**self._base_payload_, "orderId": orderId}

    def cancel_all_orders(self, symbol: str) -> Dict:
        return {**self._base_payload_, "symbol": symbol}

    def set_leverage(self, symbol, leverage: int) -> Dict:
        return {
            **self._base_payload_,
            "symbol": symbol,
            "buyLeverage": str(leverage),
            "sellLeverage": str(leverage),
        }

    def ohlcv(self, symbol: str, interval: int) -> Dict:
        return {
            **self._base_payload_,
            "symbol": symbol,
            "interval": str(interval),
            "limit": "1000",  # NOTE: [1, 1000]. Default: 200
        }

    def trades(self, symbol: str) -> Dict:
        return {
            **self._base_payload_,
            "symbol": symbol,
            "limit": "1000",  # NOTE: [1,1000], default: 500
        }

    def book(self, symbol: str) -> Dict:
        return {
            **self._base_payload_,
            "symbol": symbol,
            "limit": "200",  # NOTE: [1, 200]. Default: 25
        }

    def instrument(self, symbol: str) -> Dict:
        return {**self._base_payload_, "symbol": symbol}

    def open_orders(self, symbol: str) -> Dict:
        return {**self._base_payload_, "symbol": symbol}

    def current_position(self, symbol: str) -> Dict:
        return {**self._base_payload_, "symbol": symbol}

    def account_info(self) -> Dict:
        return self._base_payload_

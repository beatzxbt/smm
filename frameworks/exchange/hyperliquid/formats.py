from typing import Dict, Optional


class HyperliquidFormats:
    def __init__(self) -> None:
        self._type_market_ = {"limit": {"tif": "GTC"}}
        self._type_limit_ = {"limit": {"tif": "ALO"}}
        self._base_payload_ = {"action": {}, "nonce": 1e12, "signature": "x" * 128}

    def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Dict:
        if tp is not None:
            raise NotImplementedError(f"Hyperliquid doesn't support attached TP's!")

        if price is None:
            raise ValueError(f"Hyperliquid requires a price with limit &/or market orders...")

        self._base_payload_["action"] = {
            "type": "order",
            "grouping": "na",
            "orders": [{
                "asset": symbol,
                "is_buy": True if side == 0.0 else False,
                "limit_px": price if type == "limit" else (price * 1.01 if side == 0.0 else price * 0.99),
                "sz": amount,
                "reduceOnly": False,
                "orderType": self._type_limit_ if type == "limit" else self._type_market_
            }]
        }

        return format

    def amend_order(
        self,
        orderId: str,
        symbol: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> Dict:
        if tp is not None:
            raise NotImplementedError(f"Hyperliquid doesn't support attached TP's!")
        
        format = {
            "type": "modify",
            "oid": orderId,
            "order": [{
                "asset": symbol,
                "is_buy": True if side == 0.0 else False,
                "limit_px": price*1.01 if side == 0.0 else False,
                "sz": amount,
                "reduceOnly": False,
                "orderType": self._limit_
            }]
        }

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

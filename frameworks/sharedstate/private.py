
import asyncio
import numpy as np
import yaml
from collections import deque


class PrivateDataSharedState:


    def __init__(self, params) -> None:
        self.binance_symbols, self.bybit_symbols, self.hyperliquid_symbols = [], [], []

        for exchange, ticker in params.symbols:
                    getattr(self, f"{exchange.lower()}_symbols").append(ticker)

        self.binance = {
            "API": self._base_api_outline(),
            "Data": {f"{symbol}": self._base_data_outline() for symbol in self.binance_symbols}
        }

        self.bybit = {
            "API": self._base_api_outline(),
            "Data": {f"{symbol}": self._base_data_outline() for symbol in self.bybit_symbols}
        }

        self.hyperliquid = {
            "API": self._base_api_outline(),
            "Data": {f"{symbol}": self._base_data_outline() for symbol in self.hyperliquid_symbols}
        }

    
    def _base_data_outline(self) -> dict:
        """
        Base dict for all exchange private data

        A new base will be spawned per symbol
        """

        return {
            "current_orders": {},
            "executions": deque(maxlen=1000),
            "position": deque(maxlen=1000),

            "position_size": 0,
            "leverage": 0,
            "unrealized_pnl": 0
        }


    def _base_api_outline(self) -> dict:
        """
        Base dict for api/rate-limit information

        Used by diff func to smartly manage orders under high load
        
        * Add rate-limit per endpoint as keys in the client *

        Do it in the format:
            self.binance{
                "API": {
                    "post-endpoint": [remaining, max, time-till-reset],
                    "amend-endpoint": [remaining, max, time-till-reset],
                    ...
                    "cancel-endpoint": [remaining, max, time-till-reset]
                }
        """

        return {
            "key": '',
            "secret": '',
            "account_balance": 0,

            "maker_fees": 0,
            "taker_fees": 0
        }

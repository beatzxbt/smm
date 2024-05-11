import asyncio
import aiohttp
import hashlib
import hmac
from typing import Dict, List, Union

from frameworks.exchange.base.client import Client
from frameworks.exchange.bybit.endpoints import BybitEndpoints


class BybitClient(Client):
    _errors_ = {
        "200": None,
        "10006": (False, "Rate limits exceeded!"),
        "10016": (False, "Bybit server error..."),
        "110001": (False, "Order doesnt exist anymore!"),
        "110012": (False, "Insufficient available balance"),
    }
    
    def __init__(self, key: str, secret: str) -> None:
        super().__init__(key, secret)
        self.endpoints = BybitEndpoints

        self._cache_partial_str_ = f"{self.key}{self.recvWindow}"
        self._cached_header_ = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-API-KEY": self.key,
            "X-BAPI-RECV-WINDOW": self.recvWindow,
            "X-BAPI-SIGN": "x" * 64
        }

    def _sign_(self, payload: str) -> Dict:
        """SHA-256 signing logic"""
        self.update_timestamp() # NOTE: Updates self.timestamp
        param_str = f"{self.timestamp}{self._cache_partial_str_}{payload}"
        hash_signature = hmac.new(
            key=self.secret.encode(), 
            msg=param_str.encode(), 
            digestmod=hashlib.sha256
        )
        self._cached_header_["X-BAPI-TIMESTAMP"] = self.timestamp
        self._cached_header_["X-BAPI-SIGN"] = hash_signature.hexdigest()
        return self._cached_header_

    def _error_handler_(self, recv: Dict) -> Dict:
        """
        Tuple(bool, error msg)

        False: Do not attempt retry, break loop
        True: Raise exception and go through standard retry loop
        """
        pass
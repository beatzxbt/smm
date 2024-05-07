import asyncio
import aiohttp
import hashlib
import hmac
from typing import Dict, List, Union

from frameworks.exchange.base.client import Client
from frameworks.exchange.bybit.endpoints import BybitEndpoints


class BybitClient(Client):
    def __init__(self, key: str, secret: str) -> None:
        self.key, self.secret = key, secret
        self.endpoints = BybitEndpoints
        super().__init__()

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

    def _error_handler_(self, response: Dict) -> Union[Dict, None]:
        """
        Tuple(bool, error msg)

        False: Do not attempt retry, break loop
        True: Raise exception and go through standard retry loop
        """
        self.err_codes["10006"] = (False, "Rate limits exceeded!")
        self.err_codes["10016"] = (False, "Bybit server error...")
        self.err_codes["110001"] = (False, "Order doesnt exist anymore!")
        self.err_codes["110012"] = (False, "Insufficient available balance")
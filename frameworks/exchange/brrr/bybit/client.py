import asyncio
import aiohttp
import hashlib
import hmac
from numpy_ringbuffer import RingBuffer
from frameworks.exchange.base.rest.client import Client
from frameworks.exchange.base.rest.ratelimits import Ratelimit
from frameworks.exchange.brrr.bybit.endpoints import endpoints
from typing import Dict, List, Union


class BybitClient(Client):

    def __init__(self, api: Dict) -> None:
        super().__init__()
        self.key, self.secret = api["key"], api["secret"]
        self.endpoints = endpoints

        self._cache_partial_str_ = f"{self.key}{self.recvWindow}"
        self._cached_header_ = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-API-KEY": self.key,
            "X-BAPI-RECV-WINDOW": self.recvWindow,
            "X-BAPI-SIGN": "x" * 64
        }
    
    @property
    def __latency__(self) -> RingBuffer:
        """Pointer to latency ring buffer in exchange API Dict"""
        return self.api["latency"]

    def _sign_(self, payload: str) -> Dict:
        """SHA-256 signing logic"""
        _ = self.update_timestamp() # NOTE: Updates self.timestamp
        param_str = f"{self.timestamp}{self._cache_partial_str_}{payload}"
        hash_signature = hmac.new(
            self.secret.encode("utf-8"), param_str.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        self._cached_header_["X-BAPI-TIMESTAMP"] = self.timestamp
        self._cached_header_["X-BAPI-SIGN"] = hash_signature
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
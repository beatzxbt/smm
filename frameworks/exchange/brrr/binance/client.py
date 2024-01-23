import asyncio
import hashlib
import hmac
from numpy_ringbuffer import RingBuffer
from frameworks.exchange.base.rest.client import Client
from frameworks.exchange.base.rest.ratelimits import Ratelimit
from frameworks.exchange.brrr.binance.endpoints import endpoints
from typing import Dict, List, Union


class BinanceClient(Client):
    def __init__(self, api: Dict) -> None:
        super().__init__()
        self.key, self.secret = api["key"], api["secret"]
        self.endpoints = endpoints

        self._cache_partial_str_ = "x" * 128
        self._cached_header_ = {
            "timestamp": self.timestamp,
            "signature": "x" * 64
        }

    def _process_latency_(self, response: Dict) -> RingBuffer:
        """Process raw response and dump latency to RingBuffer"""
        return self.api["latency"]

    def _sign_(self, payload: str) -> Dict:
        """SHA-256 signing logic"""
        _ = self.update_timestamp()  # NOTE: Updates self.timestamp
        hash_signature = hmac.new(
            self.secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        self._cached_header_["timestamp"] = self.timestamp
        self._cached_header_["signature"] = hash_signature
        return self._cached_header_

    def _error_handler_(self, response: Dict) -> Union[Dict, None]:
        """
        Tuple(bool, error msg)

        False: Do not attempt retry, break loop
        True: Raise exception and go through standard retry loop
        """
        # need to be replaced with binance errors (current bybit)!
        self.err_codes["10006"] = (False, "Rate limits exceeded!")
        self.err_codes["10016"] = (False, "Bybit server error...")
        self.err_codes["110001"] = (False, "Order doesnt exist anymore!")
        self.err_codes["110012"] = (False, "Insufficient available balance")

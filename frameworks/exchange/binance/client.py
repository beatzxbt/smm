import asyncio
import hashlib
import hmac
from frameworks.tools.logging import time_ms
from frameworks.exchange.base.client import Client
from frameworks.exchange.binance.endpoints import BinanceEndpoints
from typing import Any, Dict, Tuple, Union, Optional


class BinanceClient(Client):
    _errors_ = {
        "200": None,
        "1003": (False, "Rate limits exceeded!"),
        "1015": (False, "Rate limits exceeded!"),
        "1008": (False, "Server overloaded..."),
        "1021": (True, "Out of recvWindow..."),
        "1111": (False, "Incorrect tick/lot size..."),
        "4029": (False, "Incorrect tick size..."),
        "4030": (False, "Incorrect lot size..."),
        "1125": (False, "Invalid listen key..."),
        "2010": (False, "Order create rejected..."),
        "2011": (False, "Order cancel rejected..."),
        "2012": (False, "Order cancel all rejected..."),
        "2013": (False, "Order does not exist..."),
        "2018": (False, "Insufficient balance..."),
    }
    
    def __init__(self, key: str, secret: str) -> None:
        super().__init__(key, secret)
        self.endpoints = BinanceEndpoints

        self._cached_header_ = {
            "timestamp": self.timestamp,
            "signature": "x" * 64
        }

    def sign_payload(self, payload: str) -> Dict:
        """SHA-256 signing logic"""
        self.update_timestamp()
        hash_signature = hmac.new(
            self.secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        self._cached_header_["timestamp"] = self.timestamp
        self._cached_header_["signature"] = hash_signature
        return self._cached_header_

    def error_handler(self, recv: Dict) -> Union[Tuple[bool, str], None]:
        """
        Tuple(bool, error msg)

        False: Do not attempt retry, break loop
        True: Raise exception and go through standard retry loop
        """
        if "code" in recv:
            return self._errors_.get(recv["code"])
        else:
            return None

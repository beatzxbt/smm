import asyncio
import hashlib
import hmac
from frameworks.tools.logging import time_ms
from frameworks.exchange.base.client import Client
from frameworks.exchange.brrr.binance.endpoints import BinanceEndpoints
from typing import Any, Dict, Tuple, Union, Optional


class BinanceClient(Client):
    def __init__(self, private: Union[Dict[str, Any], bool]=False) -> None:
        super().__init__()
        self.private = private
        self.endpoints = BinanceEndpoints

        if isinstance(self.private, Dict):
            self.key = self.private["binance"]["API"]["key"]
            self.secret = self.private["binance"]["API"]["secret"]

            self._ratelimits_format_ = {
                "remaining": 0,
                "reset": 0,
                "max": 0
            }
            
            self._ratelimits_ = {
                self.endpoints["createOrder"]: {**self._ratelimits_format_},
                self.endpoints["amendOrder"]: {**self._ratelimits_format_},
                self.endpoints["cancelOrder"]: {**self._ratelimits_format_},
                self.endpoints["cancelAllOrders"]: {**self._ratelimits_format_}
            }
        else:
            self.key = ""
            self.secret = ""

        self._cached_header_ = {
            "timestamp": self.timestamp,
            "signature": "x" * 64
        }

        self._errors_ = {
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

    def _sign_(self, payload: str) -> Dict:
        """SHA-256 signing logic"""
        self.update_timestamp()
        hash_signature = hmac.new(
            self.secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        self._cached_header_["timestamp"] = self.timestamp
        self._cached_header_["signature"] = hash_signature
        return self._cached_header_

    def _error_handler_(self, recv: Dict) -> Union[Tuple[bool, str], None]:
        """
        Tuple(bool, error msg)

        False: Do not attempt retry, break loop
        True: Raise exception and go through standard retry loop
        """
        if "code" in recv:
            return self._errors_.get(recv["code"])
        else:
            return None

    def _latency_handler(self, recv: Dict) -> None:
        """Process raw response and dump latency to RingBuffer"""
        self.api["latency"].append(time_ms() - float(recv["timestamp"]))

    def _ratelimit_handler_(
        self, 
        recv: Optional[Dict]=None,
        method: Optional[str]=None, 
        endpoint: Optional[str]=None
    ) -> None:
        if method is not None and endpoint is not None:
            self._ratelimits_.get(f"{method}|{endpoint}")

import orjson
import hashlib
import hmac
from typing import Dict, Tuple

from frameworks.exchange.base.client import Client


class BinanceClient(Client):
    recv_window = 1000

    errors: Dict[int, Tuple[bool, str]] = {
        0: (False, ""),
        200: (False, ""),
        1003: (False, "Rate limits exceeded!"),
        1015: (False, "Rate limits exceeded!"),
        1008: (True, "Server overloaded..."),
        1021: (True, "Out of recvWindow..."),
        1111: (False, "Incorrect tick/lot size..."),
        4029: (False, "Incorrect tick/lot size..."),
        4030: (False, "Incorrect tick/lot size..."),
        1125: (False, "Invalid listen key..."),
        2010: (False, "Order create rejected..."),
        2011: (False, "Order cancel rejected..."),
        2012: (False, "Order cancel all rejected..."),
        2013: (False, "Order does not exist..."),
        2014: (False, "Invalid API key format"),
        2018: (False, "Insufficient balance..."),
        3000: (True, "System busy. Please try again later."),
        3001: (False, "Trading is suspended for this symbol."),
        3002: (False, "Order has been filled or canceled."),
        3003: (False, "Order was not found."),
        3004: (False, "Insufficient funds in your account."),
        3005: (False, "Margin call failed. Please add more funds."),
        3006: (False, "Position size exceeds the maximum limit."),
        3007: (False, "Position already exists. Cannot open a new position."),
        3008: (False, "Duplicate order detected."),
        3009: (False, "Invalid leverage setting."),
        3010: (False, "Position liquidation in progress."),
        3011: (False, "API key permissions are insufficient for this action."),
        3012: (False, "Order amount is too small."),
        3013: (False, "Order amount exceeds the maximum limit."),
        3014: (False, "The trading pair is not available."),
        3015: (False, "The order price is out of the allowed range."),
    }

    def __init__(self, api_key: str, api_secret: str) -> None:
        super().__init__(api_key, api_secret)

        self.base_headers = {
            "X-MBX-APIKEY": self.api_key,
        }

    def sign_headers(self, method, headers):
        hash_signature = hmac.new(
            key=self.api_secret.encode(),
            msg=orjson.dumps(headers),
            digestmod=hashlib.sha256,
        )
        headers["signature"] = hash_signature.hexdigest()
        return headers

    def error_handler(self, recv):
        error_code = int(recv.get("code", 0))
        return self.errors.get(
            error_code,
            (False, f"Unknown error code: {error_code}")
        )
        
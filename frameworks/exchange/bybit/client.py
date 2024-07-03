import orjson
import hashlib
import hmac
from urllib.parse import urlencode

from typing import Dict, Tuple
from frameworks.exchange.base.client import Client


class BybitClient(Client):
    recv_window = 1000

    errors: Dict[int, Tuple[bool, str]] = {
        0: (False, ""),
        200: (False, ""),
        10001: (False, "Illegal category"),
        10006: (False, "Rate limits exceeded!"),
        10016: (True, "Bybit server error..."),
        10010: (False, "Unmatched IP, check your API key's bound IP addresses."),
        110001: (False, "Order doesn't exist anymore!"),
        110012: (False, "Insufficient available balance"),
    }

    def __init__(self, api_key: str, api_secret: str) -> None:
        super().__init__(api_key, api_secret)

        self.headers_template = {
            **self.default_headers,
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-SIGN": "",
            "X-BAPI-RECV-WINDOW": self.recv_window,
        }

    def sign_headers(self, method, headers):
        self.update_timestamp()
        param_str = f"{self.timestamp}{self.api_key}{str(self.recv_window)}"

        match method:
            case "GET":
                param_str += urlencode(headers)

            case "POST":
                param_str += orjson.dumps(headers).decode()

            case _:
                raise ValueError("Invalid method for signing")

        hash_signature = hmac.new(
            key=self.api_secret.encode(),
            msg=param_str.encode(),
            digestmod=hashlib.sha256,
        )

        self.headers_template["X-BAPI-TIMESTAMP"] = str(self.timestamp)
        self.headers_template["X-BAPI-SIGN"] = hash_signature.hexdigest()
        return self.headers_template.copy()

    def error_handler(self, recv):
        return self.errors.get(
            int(recv.get("retCode", 0)),
            (False, "Unknown error code...")
        )

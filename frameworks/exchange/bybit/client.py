import orjson
import hashlib
import hmac
from urllib.parse import urlencode

from frameworks.exchange.base.client import Client


class BybitClient(Client):
    recv_window = "5000"

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
        param_str = f"{self.timestamp}{self.api_key}{self.recv_window}"

        match method:
            case "GET":
                param_str += urlencode(headers)

            case "POST":
                param_str += orjson.dumps(headers).decode()

            case _:
                raise Exception("Invalid method for signing")

        hash_signature = hmac.new(
            key=self.api_secret.encode(),
            msg=param_str.encode(),
            digestmod=hashlib.sha256,
        )

        self.headers_template["X-BAPI-TIMESTAMP"] = str(self.timestamp)
        self.headers_template["X-BAPI-SIGN"] = hash_signature.hexdigest()
        return self.headers_template.copy()

    def error_handler(self, recv):
        match int(recv.get("retCode", 0)):
            case 0 | 200:
                return (False, "")

            case 10001:
                return (False, "Illegal category")

            case 10006:
                return (False, "Rate limits exceeded!")

            case 10016:
                return (True, "Bybit server error...")

            case 10010:
                return (False, "Unmatched IP, check your API key's bound IP addresses.")
            
            case 110001:
                return (False, "Order doesn't exist anymore!")

            case 110012:
                return (False, "Insufficient available balance")

            case _:
                return (False, "Unknown error code...")

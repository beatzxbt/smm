import asyncio
import orjson
import hashlib
import hmac

from frameworks.exchange.base.client import Client


class BybitClient(Client):
    def __init__(self, api_key: str, api_secret: str) -> None:
        super().__init__(api_key, api_secret)

        self.header_template = {
            **self.default_headers,
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-SIGN": "",
            "X-BAPI-RECV-WINDOW": "5000",
        }

    def sign_payload(self, payload):
        self.update_timestamp()
        payload_bytes = f"{self.timestamp}{self.api_key}5000".encode() + orjson.dumps(payload)
        hash_signature = hmac.new(
            key=self.api_secret.encode(),
            msg=payload_bytes,
            digestmod=hashlib.sha256
        )
        self.header_template["X-BAPI-TIMESTAMP"] = self.timestamp
        self.header_template["X-BAPI-SIGN"] = hash_signature.hexdigest()
        return self.header_template

    def error_handler(self, recv):
        match int(recv.get("retCode")):
            case 0 | 200:
                return (False, "")
            
            case 10001:
                return (False, "Illegal category")
            
            case 10006:
                return (False, "Rate limits exceeded!")
            
            case 10016:
                return (False, "Bybit server error...")
            
            case 110001:
                return (False, "Order doesn't exist anymore!")
            
            case 110012:
                return (False, "Insufficient available balance")
            
            case _:
                return (False, "Unknown error code...")

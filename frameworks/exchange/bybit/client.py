import asyncio
import aiohttp
import hashlib
import hmac
from typing import Dict, List, Union, Tuple, Any

from frameworks.exchange.base.client import Client


class BybitClient(Client):
    def __init__(self, api_key: str, api_secret: str) -> None:
        super().__init__(api_key, api_secret)

        self.header_template = {
            "X-BAPI-TIMESTAMP": self.timestamp,
            "X-BAPI-API-KEY": self.key,
            "X-BAPI-RECV-WINDOW": self.recvWindow,
            "X-BAPI-SIGN": "x" * 64
        }

    def sign_payload(self, payload: str) -> Dict[str, Any]:
        self.update_timestamp()  # NOTE: Updates self.timestamp
        param_str = f"{self.timestamp}{self.key}{self.recvWindow}{payload}"
        hash_signature = hmac.new(
            key=self.api_secret.encode(),
            msg=payload.encode(),
            digestmod=hashlib.sha256
        )
        self.header_template["X-BAPI-TIMESTAMP"] = self.timestamp
        self.header_template["X-BAPI-SIGN"] = hash_signature.hexdigest()
        return self.header_template

    def error_handler(self, recv: Dict[str, Any]) -> Tuple[bool, str]:
        match recv.get("code"):
            case "200":
                return (False, "")
            
            case "10006":
                return (False, "Rate limits exceeded!")
            
            case "10016":
                return (False, "Bybit server error...")
            
            case "110001":
                return (False, "Order doesn't exist anymore!")
            
            case "110012":
                return (False, "Insufficient available balance")
            
            case _:
                return (False, "Unknown error code...")

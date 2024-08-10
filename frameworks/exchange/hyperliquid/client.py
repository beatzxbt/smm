import msgpack
from decimal import Decimal
from eth_account import *
from eth_account.messages import encode_structured_data
from eth_utils import keccak, to_hex
from typing import Dict

from frameworks.exchange.base.client import Client
from frameworks.exchange.hyperliquid.endpoints import HyperliquidEndpoints
from frameworks.tools.logging import time_ms

class HyperliquidClient(Client):
    def __init__(self, api_key: str, api_secret: str) -> None:
        super().__init__(api_key, api_secret)
        self.endpoints = HyperliquidEndpoints

        self.base_data = {
            "domain": {
                "chainId": 1337,
                "name": "Exchange",
                "verifyingContract": "0x0000000000000000000000000000000000000000",
                "version": "1",
            },
            "types": {
                "Agent": [
                    {"name": "source", "type": "string"},
                    {"name": "connectionId", "type": "bytes32"},
                ],
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
            },
            "primaryType": "Agent",
            "message": "",  # NOTE: Phantom agent comes here
        }

        self.wallet = None
        self.symbol_key = None

    def set_wallet(self, wallet: LocalAccount) -> None:
        self.wallet = wallet

    def set_symbol_key(self, symbol_key: int) -> None:
        self.symbol_key = symbol_key

    def _float_to_rounded_str_(self, num: float) -> str:
        return str(round(num, 8))
    
    def _action_hash_(self, action, timestamp: str) -> bytes:
        data = msgpack.packb(action)
        data += int(timestamp).to_bytes(8, "big")
        data += b"\x00"
        return keccak(data)
    
    def _sign_inner_(self, wallet: LocalAccount, data) -> Dict:
        structured_data = encode_structured_data(data)
        signed = wallet.sign_message(structured_data)
        return {"r": to_hex(signed["r"]), "s": to_hex(signed["s"]), "v": signed["v"]}

    def _construct_phantom_agent_(hash: bytes) -> Dict:
        return {"source": "a", "connectionId": hash}

    def _sign_l1_action_(self, wallet, action, active_pool, nonce):
        hash = self._action_hash_(action, active_pool, nonce)
        self.base_data["message"] = self._construct_phantom_agent_(hash)
        return sign_inner(wallet, data)
    
    def _order_type_to_wire_(self, orderType: str) -> Dict:
        if "limit" in order_type:
            return {"limit": order_type["limit"]}
        
        elif "trigger" in order_type:
            return {
                "trigger": {
                    "isMarket": order_type["trigger"]["isMarket"],
                    "triggerPx": float_to_wire(order_type["trigger"]["triggerPx"]),
                    "tpsl": order_type["trigger"]["tpsl"],
                }
            }
    def sign_order_payload(self, order: Dict) -> Dict:
        order_wire = {
            "a": self.symbol_key,
            "b": order["is_buy"],
            "p": self._float_to_rounded_str_(order["limit_px"]),
            "s": self._float_to_rounded_str_(order["sz"]),
            "r": order["reduce_only"],
            "t": order_type_to_wire(order["order_type"]),
        }

        if "cloid" in order and order["cloid"] is not None:
            order_wire["c"] = order["cloid"].to_raw()

        timestamp = time_ms()

        order_action = {
            "type": "order",
            "orders": order_wires,
            "grouping": "na",
        }

        signature = sign_l1_action(
            self.wallet,
            order_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )

        payload = {
            "action": order_action,
            "nonce": timestamp,
            "signature": signature,
            "vaultAddress": self.vault_address,
        }
        
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
        match int(recv.get("retCode")):
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

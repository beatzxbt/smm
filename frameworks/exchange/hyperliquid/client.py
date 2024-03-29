import time
import asyncio
from eth_abi import encode
from eth_account.messages import encode_structured_data
from eth_utils import keccak, to_hex
from numpy_ringbuffer import RingBuffer
from frameworks.exchange.base.rest.client import Client
from frameworks.exchange.base.rest.ratelimits import RateLimitManager
from frameworks.exchange.brrr.hyperliquid.endpoints import endpoints
from typing import Dict, Tuple, Any

class HyperliquidClient(Client):
    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
    SIGNATURE_TYPES = [
        "uint32",
        "bool",
        "uint256",
        "uint256",
        "bool",
        "uint8",
        "uint256",
        "address",
        "uint64"
    ]

    def __init__(self, api: Dict) -> None:
        super().__init__()
        self.wallet, _ = api["key"], api["secret"]
        self.endpoints = endpoints
    
        self.l1_signing_data = {
            "domain": {
                "chainId": 1337,
                "name": "Exchange",
                "verifyingContract": self.ZERO_ADDRESS,
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
            "message": None,
        }

    def _sign_(self, order_request, asset: int) -> Dict:
        order_spec = self._order_request_to_order_spec_(order_request, asset)
        order_wire = self._order_spec_to_order_wire_(order_spec)
        signature_data = self._order_spec_preprocessing_(order_wire)
        return self._sign_l1_action_(self.wallet, signature_data, None, 0)

    def _order_type_to_tuple_(self, order_type) -> Tuple[int, float]:
        if "limit" in order_type:
            tif = order_type["limit"]["tif"]
            if tif == "Gtc":
                return 2, 0
            elif tif == "Alo":
                return 1, 0
            elif tif == "Ioc":
                return 3, 0

    def _order_spec_preprocessing_(self, order_wire) -> list:
        return [
            order_wire["asset"],
            order_wire["isBuy"],
            self._float_to_int_for_hashing_(float(order_wire["limitPx"])),
            self._float_to_int_for_hashing_(float(order_wire["sz"])),
            order_wire["reduceOnly"],
            self._order_type_to_tuple_(order_wire["orderType"])[0],
            self._float_to_int_for_hashing_(
                self._order_type_to_tuple_(order_wire["orderType"])[1]
            )
        ]

    def _order_request_to_order_spec_(self, order, asset: int) -> Dict:
        return {
            "order": {
                "asset": asset,
                "isBuy": order["is_buy"],
                "reduceOnly": order["reduce_only"],
                "limitPx": order["limit_px"],
                "sz": order["sz"],
            },
            "orderType": order["order_type"],
        }

    def _order_spec_to_order_wire_(self, order_spec: Dict) -> Dict:
        order = order_spec["order"]
        return {
            "asset": order["asset"],
            "isBuy": order["isBuy"],
            "limitPx": self._float_to_wire_(order["limitPx"]),
            "sz": self._float_to_wire_(order["sz"]),
            "reduceOnly": order["reduceOnly"],
            "orderType": self._order_type_to_wire_(order_spec["orderType"]),
        }

    def _order_type_to_wire_(self, order_type: Dict) -> Dict:
        if "limit" in order_type:
            return {"limit": order_type["limit"]}

    def _sign_l1_action_(self, wallet, signature_data, active_pool, nonce) -> Dict[str, any]:
        signature_data.append(self.ZERO_ADDRESS if active_pool is None else active_pool)
        signature_data.append(nonce)
        phantom_agent = self._construct_phantom_agent_(signature_data)
        self.L1SigningData["message"] = phantom_agent
        return self._sign_inner_(wallet, self.L1SigningData)

    def _construct_phantom_agent_(self, signature_data):
        connection_id = encode(["uint32", "bool", "uint256", "uint256", "bool", "uint8", "uint256", "address", "uint64"], signature_data)
        return {"source": "a", "connectionId": keccak(connection_id)}

    def _sign_inner_(self, wallet, data):
        structured_data = encode_structured_data(data)
        signed = wallet.sign_message(structured_data)
        return {"r": to_hex(signed.r), "s": to_hex(signed.s), "v": signed.v}

    def _float_to_wire_(self, x: float) -> str:
        return "{:.8f}".format(x)

    def _float_to_int_for_hashing_(self, x: float) -> int:
        return round(x * 1e8)

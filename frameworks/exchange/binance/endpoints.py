
from dataclasses import dataclass


@dataclass
class BaseEndpoints:
    MAINNET1 = "https://fapi.binance.com"


@dataclass
class WsStreamLinks:
    SPOT_PUBLIC_STREAM = "wss://stream.binance.com:9443"
    FUTURES_PUBLIC_STREAM = "wss://fstream.binance.com"


@dataclass
class PrivatePostLinks:
    CREATE_ORDER = "/fapi/v1/order"
    AMEND_ORDER = "/fapi/v1/order"
    CANCEL_SINGLE = "/fapi/v1/order"
    CANCEL_ALL = "/fapi/v1/allOpenOrders"
    

from dataclasses import dataclass


@dataclass
class BaseEndpoints:
    MAINNET1 = "https://api.hyperliquid.xyz"
    TESTNET1 = "https://api.hyperliquid-testnet.xyz"


@dataclass
class WsStreamLinks:
    COMBINED_FUTURES_STREAM = "wss://api.hyperliquid.xyz/ws"


@dataclass
class PrivatePostLinks:
    CREATE_ORDER = "/exchange"
    CANCEL_SINGLE = "/exchange"
    
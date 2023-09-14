
from dataclasses import dataclass


@dataclass
class WsStreamLinks:
    SPOT_PUBLIC_STREAM = "wss://stream.binance.com:9443"
    FUTURES_PUBLIC_STREAM = "wss://fstream.binance.com"
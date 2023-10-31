
from dataclasses import dataclass


@dataclass
class BaseEndpoints:
    MAINNET1 = "https://api.bybit.com"
    MAINNET2 = "https://api.bytick.com"


@dataclass
class WsStreamLinks:
    SPOT_PUBLIC_STREAM = "wss://stream.bybit.com/v5/public/spot"
    FUTURES_PUBLIC_STREAM = "wss://stream.bybit.com/v5/public/linear"
    COMBINED_PRIVATE_STREAM = "wss://stream.bybit.com/v5/private"


@dataclass
class PrivatePostLinks:
    CREATE_ORDER = "/v5/order/create"
    CREATE_BATCH = "/v5/order/create-batch"
    AMEND_ORDER = "/v5/order/amend"
    AMEND_BATCH = "/v5/order/amend-batch"
    CANCEL_SINGLE = "/v5/order/cancel"
    CANCEL_BATCH = "/v5/order/cancel-batch"
    CANCEL_ALL = "/v5/order/cancel-all"
    
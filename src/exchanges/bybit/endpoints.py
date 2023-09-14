
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
class PrivateGetLinks:
    OPEN_ORDERS = "/v5/order/realtime"
    CURRENT_POSITION = "/v5/position/list"
    CLOSED_PNL = "/v5/position/closed-pnl"
    WALLET_BALANCE = "/v5/account/wallet-balance"


@dataclass
class PrivatePostLinks:
    CREATE_ORDER = "/v5/order/create"
    CREATE_BATCH = "/unified/v3/private/order/create-batch"
    AMEND_ORDER = "/v5/order/amend"
    AMEND_BATCH = "/unified/v3/private/order/replace-batch"
    CANCEL_SINGLE = "/v5/order/cancel"
    CANCEL_BATCH = "/unified/v3/private/order/cancel-batch"
    CANCEL_ALL = "/v5/order/cancel-all"
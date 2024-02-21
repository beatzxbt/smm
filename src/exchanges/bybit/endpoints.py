from dataclasses import dataclass
import os

if_testnet = "-testnet" if os.getenv("TESTNET") == "True" else ""

@dataclass
class BaseEndpoints:
    MAINNET1 = f"https://api{if_testnet}.bybit.com"
    MAINNET2 = f"https://api{if_testnet}.bytick.com"

@dataclass
class WsStreamLinks:
    domain = f"stream{if_testnet}.bybit.com"
    SPOT_PUBLIC_STREAM = f"wss://{domain}/v5/public/spot"
    FUTURES_PUBLIC_STREAM = f"wss://{domain}/v5/public/linear"
    COMBINED_PRIVATE_STREAM = f"wss://{domain}/v5/private"

@dataclass
class PrivateGetLinks:
    OPEN_ORDERS = "/v5/order/realtime"
    CURRENT_POSITION = "/v5/position/list"
    CLOSED_PNL = "/v5/position/closed-pnl"
    WALLET_BALANCE = "/v5/account/wallet-balance"

@dataclass
class PrivatePostLinks:
    CREATE_ORDER = "/v5/order/create"
    CREATE_BATCH = "/v5/order/create-batch"
    AMEND_ORDER = "/v5/order/amend"
    AMEND_BATCH = "/v5/order/amend-batch"
    CANCEL_SINGLE = "/v5/order/cancel"
    CANCEL_BATCH = "/v5/order/cancel-batch"
    CANCEL_ALL = "/v5/order/cancel-all"
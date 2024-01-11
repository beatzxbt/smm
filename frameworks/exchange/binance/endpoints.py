from dataclasses import dataclass

@dataclass
class BaseEndpoints:
    MAIN1 = "https://fapi.binance.com"

@dataclass
class WsEndpoints:
    SPOT_PUBLIC_STREAM = "wss://stream.binance.com:9443"
    FUTURES_PUBLIC_STREAM = "wss://fstream.binance.com"

@dataclass
class ClientEndpoints:
    CREATE_ORDER = "/fapi/v1/order" # NOTE: POST
    AMEND_ORDER = "/fapi/v1/order" # NOTE: PUT
    CANCEL_ORDER = "/fapi/v1/order" # NOTE: DELETE
    CANCEL_ALL_ORDER = "/fapi/v1/allOpenOrders" # NOTE: DELETE
    
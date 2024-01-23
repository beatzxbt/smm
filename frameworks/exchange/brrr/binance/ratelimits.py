from frameworks.exchange.base.rest.ratelimits import Ratelimit

RateLimitMap = {
    "createOrder": ("/fapi/v1/order", "POST"),                
    "amendOrder": ("/fapi/v1/order", "PUT"),                 
    "cancelOrder": ("/fapi/v1/order", "DELETE"),                
    "cancelAllOrders": ("/fapi/v1/allOpenOrders", "DELETE")
}

RateLimitFormat = {
    "remaining": 0,
    "reset": 0,
    "max": 0
}

class BinanceRateLimitManager(Ratelimit):
    def __init__(self) -> None:
        pass
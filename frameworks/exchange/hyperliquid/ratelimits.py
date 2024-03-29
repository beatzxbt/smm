
RateLimitMap = {
    "createOrder": ("/fapi/v1/order", "POST"),                
    "amendOrder": ("/fapi/v1/order", "PUT"),                 
    "cancelOrder": ("/fapi/v1/order", "DELETE"),                
    "cancelAllOrders": ("/fapi/v1/allOpenOrders", "DELETE")
}
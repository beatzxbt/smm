
BinanceEndpoints = {
    "main1": "https://fapi.binance.com",
    "pub_ws": "wss://fstream.binance.com",
    "priv_ws": "wss://fstream.binance.com",

    "ping": ("/fapi/v1/ping", "GET"),                         
    "exchangeInfo": ("/fapi/v1/exchangeInfo", "GET"),         
    "instrumentInfo": ("/fapi/v1/exchangeInfo", "GET"), # NOTE: tick/lot sizes within ["symbols"]["filters"]
    "orderbook": ("/fapi/v1/depth", "GET"),                   
    "trades": ("/fapi/v1/trades", "GET"),                     
    "ohlcv": ("/fapi/v1/klines", "GET"),                      
    "allOpenOrders": ("/fapi/v1/openOrders", "GET"),          
    "accountInfo": ("/fapi/v2/account", "GET"),               
    "positionInfo": ("/fapi/v2/positionRisk", "GET"),         
    "feeRate": ("/fapi/v1/commissionRate", "GET"),            

    "createOrder": ("/fapi/v1/order", "POST"),                
    "amendOrder": ("/fapi/v1/order", "PUT"),                 
    "cancelOrder": ("/fapi/v1/order", "DELETE"),                
    "cancelAllOrders": ("/fapi/v1/allOpenOrders", "DELETE"),    
    "setLeverage": ("/fapi/v1/leverage", "POST"),             
}
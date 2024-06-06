from frameworks.exchange.base.endpoints import Endpoints


class BinanceEndpoints(Endpoints):
    def __init__(self) -> None:
        super().__init__()

        self.load_base(
            main="https://fapi.binance.com",
            public_ws="wss://fstream.binance.com/ws",
            private_ws="wss://fstream.binance.com/ws",
        )

        self.load_required(
            createOrder={"method": "POST", "url": "/fapi/v1/order"},
            amendOrder={"method": "PUT", "url": "/fapi/v1/order"},
            cancelOrder={"method": "DELETE", "url": "/fapi/v1/order"},
            cancelAllOrders={"method": "DELETE", "url": "/fapi/v1/allOpenOrders"},
            getOrderbook={"method": "GET", "url": "/fapi/v1/depth"},
            getTrades={"method": "GET", "url": "/fapi/v1/trades"},
            getOhlcv={"method": "GET", "url": "/fapi/v1/klines"},
            getTicker={"method": "GET", "url": "/fapi/v1/premiumIndex"},
            getOpenOrders={"method": "GET", "url": "/fapi/v1/openOrders"},
            getPosition={"method": "GET", "url": "/fapi/v2/positionRisk"},
        )

        self.load_additional(
            accountInfo={"method": "GET", "url": "/fapi/v2/account"},
            feeRate={"method": "GET", "url": "/fapi/v1/commissionRate"},
            listenKey={"method": "POST", "url": "/fapi/v1/listenKey"},
            pingListenKey={"method": "PUT", "url": "/fapi/v1/listenKey"},
            setLeverage={"method": "POST", "url": "/fapi/v1/leverage"},
        )

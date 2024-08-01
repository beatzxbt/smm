from frameworks.exchange.base.endpoints import Endpoint, Endpoints


class BinanceEndpoints(Endpoints):
    def __init__(self) -> None:
        super().__init__()

        self.load_base(
            rest=Endpoint(url="https://fapi.binance.com", method="NONE"),
            public_ws=Endpoint(url="wss://fstream.binance.com/ws", method="NONE"),
            private_ws=Endpoint(url="wss://fstream.binance.com/ws", method="NONE"),
        )

        self.load_required(
            createOrder=Endpoint(url="/fapi/v1/order", method="POST"),
            amendOrder=Endpoint(url="/fapi/v1/order", method="PUT"),
            cancelOrder=Endpoint(url="/fapi/v1/order", method="DELETE"),
            cancelAllOrders=Endpoint(url="/fapi/v1/allOpenOrders", method="DELETE"),
            getOrderbook=Endpoint(url="/fapi/v1/depth", method="GET"),
            getTrades=Endpoint(url="/fapi/v1/trades", method="GET"),
            getOhlcv=Endpoint(url="/fapi/v1/klines", method="GET"),
            getTicker=Endpoint(url="/fapi/v1/premiumIndex", method="GET"),
            getOpenOrders=Endpoint(url="/fapi/v1/openOrders", method="GET"),
            getPosition=Endpoint(url="/fapi/v2/positionRisk", method="GET"),
        )

        self.load_additional(
            ping=Endpoint(url="/fapi/v1/ping", method="GET"),
            batchCreateOrders=Endpoint(url="/fapi/v1/batchOrders", method="POST"),
            batchAmendOrders=Endpoint(url="/fapi/v1/batchOrders", method="PUT"),
            batchCancelOrders=Endpoint(url="/fapi/v1/batchOrders", method="DELETE"),
            exchangeInfo=Endpoint(url="/fapi/v1/exchangeInfo", method="GET"),
            accountInfo=Endpoint(url="/fapi/v2/account", method="GET"),
            listenKey=Endpoint(url="/fapi/v1/listenKey", method="POST"),
            pingListenKey=Endpoint(url="/fapi/v1/listenKey", method="PUT"),
            setLeverage=Endpoint(url="/fapi/v1/leverage", method="POST")
        )

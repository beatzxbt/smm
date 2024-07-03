from frameworks.exchange.base.endpoints import Endpoints


class OkxEndpoints(Endpoints):
    def __init__(self) -> None:
        super().__init__()

        self.load_base(
            main="https://www.okx.com",
            public_ws="wss://ws.okx.com:8443/ws/v5/public",
            private_ws="wss://ws.okx.com:8443/ws/v5/private",
        )

        self.load_required(
            createOrder={"method": "POST", "url": "/api/v5/trade/order"},
            amendOrder={"method": "POST", "url": "/api/v5/trade/amend-order"},
            cancelOrder={"method": "POST", "url": "/api/v5/trade/cancel-order"},
            cancelAllOrders={"method": "POST", "url": "/api/v5/trade/cancel-batch-orders"},
            getOrderbook={"method": "GET", "url": "/api/v5/market/books"},
            getTrades={"method": "GET", "url": "/api/v5/market/trades"},
            getTicker={"method": "GET", "url": "/api/v5/market/ticker"},
            getOhlcv={"method": "GET", "url": "/api/v5/market/candles"},
            getOpenOrders={"method": "GET", "url": "/api/v5/trade/orders-pending"},
            getPosition={"method": "GET", "url": "/api/v5/account/positions"},
        )

        self.load_additional(
            ping={"method": "GET", "url": "/api/v5/public/time"},
            batchCreateOrders={"method": "POST", "url": "/api/v5/trade/order"},
            batchAmendOrders={"method": "POST", "url": "/api/v5/trade/amend-batch-orders"},
            batchCancelOrders={"method": "POST", "url": "/api/v5/trade/cancel-batch-orders"},
            getInstrumentInfo={"method": "GET", "url": "/api/v5/public/instruments"},
            getAccountInfo={"method": "GET", "url": "/api/v5/account/balance"},
            setLeverage={"method": "POST", "url": "/api/v5/account/set-leverage"},
        )

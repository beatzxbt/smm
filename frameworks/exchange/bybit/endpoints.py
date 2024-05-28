from frameworks.exchange.base.endpoints import Endpoints


class BybitEndpoints(Endpoints):
    def __init__(self) -> None:
        super().__init__()

        self.load_base(
            main="https://api.bybit.com",
            public_ws="wss://stream.bybit.com/v5/public/linear",
            private_ws="wss://stream.bybit.com/v5/private",
        )

        self.load_required(
            createOrder={"method": "POST", "url": "/v5/order/create"},
            amendOrder={"method": "POST", "url": "/v5/order/amend"},
            cancelOrder={"method": "POST", "url": "/v5/order/cancel"},
            cancelAllOrders={"method": "POST", "url": "/v5/order/cancel-all"},
            getOrderbook={"method": "GET", "url": "/v5/market/orderbook"},
            getTrades={"method": "GET", "url": "/v5/market/recent-trade"},
            getTicker={"method": "GET", "url": "/v5/market/tickers"},
            getOhlcv={"method": "GET", "url": "/v5/market/kline"},
            getOpenOrders={"method": "GET", "url": "/v5/order/realtime"},
            getPosition={"method": "GET", "url": "/v5/position/list"},
        )

        self.load_additional(
            ping={"method": "GET", "url": "/v5/market/time"},
            getInstrumentInfo={"method": "GET", "url": "/v5/market/instruments-info"},
            getAccountInfo={"method": "GET", "url": "/v5/account/wallet-balance"},
            setLeverage={"method": "POST", "url": "/v5/position/set-leverage"},
        )

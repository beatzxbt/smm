from frameworks.exchange.base.endpoints import Endpoint, Endpoints


class BybitEndpoints(Endpoints):
    def __init__(self) -> None:
        super().__init__()

        self.load_base(
            rest=Endpoint(url="https://api.bybit.com", method="NONE"),
            public_ws=Endpoint(url="wss://stream.bybit.com/v5/public/linear", method="NONE"),
            private_ws=Endpoint(url="wss://stream.bybit.com/v5/private", method="NONE")
        )

        self.load_required(
            createOrder=Endpoint(url="/v5/order/create", method="POST"),
            amendOrder=Endpoint(url="/v5/order/amend", method="POST"),
            cancelOrder=Endpoint(url="/v5/order/cancel", method="POST"),
            cancelAllOrders=Endpoint(url="/v5/order/cancel-all", method="POST"),
            getOrderbook=Endpoint(url="/v5/market/orderbook", method="GET"),
            getTrades=Endpoint(url="/v5/market/recent-trade", method="GET"),
            getTicker=Endpoint(url="/v5/market/tickers", method="GET"),
            getOhlcv=Endpoint(url="/v5/market/kline", method="GET"),
            getOpenOrders=Endpoint(url="/v5/order/realtime", method="GET"),
            getPosition=Endpoint(url="/v5/position/list", method="GET"),
        )

        self.load_additional(
            ping=Endpoint(url="/v5/market/time", method="GET"),
            batchCreateOrders=Endpoint(url="/v5/order/create-batch", method="POST"),
            batchAmendOrders=Endpoint(url="/v5/order/amend-batch", method="POST"),
            batchCancelOrders=Endpoint(url="/v5/order/cancel-batch", method="POST"),
            getInstrumentInfo=Endpoint(url="/v5/market/instruments-info", method="GET"),
            getAccountInfo=Endpoint(url="/v5/account/wallet-balance", method="GET"),
            setLeverage=Endpoint(url="/v5/position/set-leverage", method="POST")
        )

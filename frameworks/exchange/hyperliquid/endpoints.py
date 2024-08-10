from frameworks.exchange.base.endpoints import Endpoint, Endpoints

class HyperliquidEndpoints(Endpoints):
    def __init__(self) -> None:
        super().__init__()

        self.load_base(
            rest=Endpoint(url="https://api.hyperliquid.xyz", method="NONE"),
            public_ws=Endpoint(url="wss://api.hyperliquid.xyz/ws", method="NONE"),
            private_ws=Endpoint(url="wss://api.hyperliquid.xyz/ws", method="NONE")
        )

        self.load_required(
            createOrder=Endpoint(url="/exchange", method="POST"),
            amendOrder=Endpoint(url="/exchange", method="POST"),
            cancelOrder=Endpoint(url="/exchange", method="POST"),
            cancelAllOrders=Endpoint(url="/exchange", method="POST"),
            getOrderbook=Endpoint(url="/info", method="GET"),
            getTrades=Endpoint(url="/info", method="GET"),
            getTicker=Endpoint(url="/info", method="GET"),
            getOhlcv=Endpoint(url="/info", method="GET"),
            getOpenOrders=Endpoint(url="/info", method="GET"),
            getPosition=Endpoint(url="/info", method="GET")
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

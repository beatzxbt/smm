from frameworks.exchange.base.endpoints import Endpoint, Endpoints

class DydxEndpoints(Endpoints):
    """Unused, using official SDK"""
    def __init__(self) -> None:
        self.load_base(
            rest=Endpoint(url="https://indexer.dydx.trade", method="NONE"), # NOTE: IGNORE
            public_ws=Endpoint(url="wss://indexer.dydx.trade/v4/ws", method="NONE"),
            private_ws=Endpoint(url="wss://indexer.dydx.trade/v4/ws", method="NONE")
        )
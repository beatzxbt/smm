from frameworks.exchange.base.endpoints import Endpoints


class DydxEndpoints(Endpoints):
    """Unused, using official SDK"""
    def __init__(self) -> None:
        self.load_base(
            main="https://dydx.trade",
            public_ws="wss://stream.bybit.com/v5/public/linear",
            private_ws="wss://stream.bybit.com/v5/private",
        )
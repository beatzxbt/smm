from dydx_v4_client.indexer.rest.constants import OrderType, OrderSide, OrderExecution
from frameworks.exchange.base.types import SideConverter, TimeInForceConverter, OrderTypeConverter


class DydxSideConverter(SideConverter):
    def __init__(self) -> None:
        super().__init__(
            BUY=OrderSide.BUY, 
            SELL=OrderSide.SELL
        )

class DydxOrderTypeConverter(OrderTypeConverter):
    def __init__(self) -> None:
        super().__init__(
            LIMIT=OrderType.LIMIT, 
            MARKET=OrderType.MARKET, 
            STOP_LIMIT=OrderType.STOP_LIMIT, 
            TAKE_PROFIT_LIMIT=OrderType.TAKE_PROFIT_LIMIT
        )

class DydxTimeInForceConverter(TimeInForceConverter):
    def __init__(self) -> None:
        super().__init__(
            GTC=OrderExecution.DEFAULT, 
            FOK=OrderExecution.FOK, 
            POST_ONLY=OrderExecution.POST_ONLY
        )
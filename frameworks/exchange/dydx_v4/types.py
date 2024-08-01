from dydx_v4_client import Order
from dydx_v4_client.indexer.rest.constants import OrderType


from frameworks.exchange.base.constants import (
    SideConverter,
    TimeInForceConverter,
    OrderTypeConverter,
    PositionDirectionConverter,
)


class DydxSideConverter(SideConverter):
    def __init__(self) -> None:
        super().__init__(
            BUY=Order.SIDE_BUY, 
            SELL=Order.SIDE_SELL
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
            GTC=Order.TIME_IN_FORCE_UNSPECIFIED, 
            FOK=Order.TIME_IN_FORCE_FILL_OR_KILL, 
            POST_ONLY=Order.TIME_IN_FORCE_POST_ONLY
        )

class DydxPositionDirectionConverter(PositionDirectionConverter):
    def __init__(self) -> None:
        super().__init__(
            LONG="LONG", 
            SHORT="SHORT"
        )
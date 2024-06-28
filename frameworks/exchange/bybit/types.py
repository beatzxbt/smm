from frameworks.exchange.base.types import (
    SideConverter,
    TimeInForceConverter,
    OrderTypeConverter,
    PositionDirectionConverter,
)


class BybitSideConverter(SideConverter):
    def __init__(self) -> None:
        super().__init__(BUY="Buy", SELL="Sell")


class BybitOrderTypeConverter(OrderTypeConverter):
    def __init__(self) -> None:
        super().__init__(
            LIMIT="Limit",
            MARKET="Market",
            STOP_LIMIT="StopLoss",
            TAKE_PROFIT_LIMIT="TakeProfit",
        )


class BybitTimeInForceConverter(TimeInForceConverter):
    def __init__(self) -> None:
        super().__init__(GTC="GTC", FOK="FOK", POST_ONLY="PostOnly")


class BybitPositionDirectionConverter(PositionDirectionConverter):
    def __init__(self) -> None:
        super().__init__(LONG="Buy", SHORT="Sell")

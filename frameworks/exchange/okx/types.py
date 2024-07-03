from frameworks.exchange.base.types import (
    SideConverter,
    TimeInForceConverter,
    OrderTypeConverter,
    PositionDirectionConverter,
)


class OkxSideConverter(SideConverter):
    def __init__(self) -> None:
        super().__init__(BUY="buy", SELL="sell")


class OkxOrderTypeConverter(OrderTypeConverter):
    def __init__(self) -> None:
        super().__init__(
            LIMIT="limit",
            MARKET="market",
            STOP_LIMIT="",
            TAKE_PROFIT_LIMIT="",
        )


class OkxTimeInForceConverter(TimeInForceConverter):
    def __init__(self) -> None:
        # NOTE: GTC is listed as "market" here as it is uncommon to send
        # non-post only maker orders, and far more common to send 
        # takers as either GTC or FOK. 
        super().__init__(GTC="market", FOK="fok", POST_ONLY="post_only")


class OkxPositionDirectionConverter(PositionDirectionConverter):
    def __init__(self) -> None:
        super().__init__(LONG="long", SHORT="short")

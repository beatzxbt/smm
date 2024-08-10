from frameworks.exchange.base.constants import (
    SideConverter,
    TimeInForceConverter,
    OrderTypeConverter,
    PositionDirectionConverter,
)


class HyperliquidSideConverter(SideConverter):
    # BUY/SELL set according to documentation showing "isBuy": boolean
    # https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint
    def __init__(self) -> None:
        super().__init__(BUY="B", SELL="A")


class HyperliquidOrderTypeConverter(OrderTypeConverter):
    def __init__(self) -> None:
        # LIMIT/MARKET set according to documentation showing "isMarket": boolean
        # https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint
        #
        # For handlers, LIMIT/MARKET will directly convert for orderType and 
        # TP/SL usage must be mapped to "trigger": "tpsl" and a default hardcoded
        # "isMarket" value. Currently there is no way to chose both LIMIT/MARKET & TP/SL.
        super().__init__(
            LIMIT=False,
            MARKET=True,
            STOP_LIMIT="sl",
            TAKE_PROFIT_LIMIT="tp",
        )


class HyperliquidTimeInForceConverter(TimeInForceConverter):
    def __init__(self) -> None:
        super().__init__(GTC="Gtc", FOK="Ioc", POST_ONLY="Alo")


class HyperliquidPositionDirectionConverter(PositionDirectionConverter):
    # No position direction mapping provided by API, handlers to determine direction 
    # using sign of positionValue (negative == SHORT, positive == LONG).

    # As position direction is larely used for entry handlers ONLY, this should
    # not cause issues down the line in future strategies.
    def __init__(self) -> None:
        super().__init__(LONG="", SHORT="")

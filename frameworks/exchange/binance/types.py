from enum import Enum
from frameworks.exchange.base.types import BaseOrderSides, BaseOrderTypes

class BinanceOrderTypes(BaseOrderTypes):
    class OrderType(Enum):
        LIMIT = 0
        MARKET = 1

class BinanceOrderSides(BaseOrderSides):
    class OrderSides(Enum):
        BUY = 0
        SELL = 1
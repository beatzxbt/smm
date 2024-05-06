from enum import Enum

from frameworks.exchange.base.types import BaseOrderSides, BaseOrderTypes

class BybitOrderTypes(BaseOrderTypes):
    class OrderType(Enum):
        Limit = 0
        Market = 1

class BybitOrderSides(BaseOrderSides):
    class OrderSides(Enum):
        Buy = 0
        Sell = 1
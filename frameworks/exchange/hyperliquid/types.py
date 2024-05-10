from enum import Enum

from frameworks.exchange.base.types import BaseOrderSides, BaseOrderTypes

# class HyperliquidOrderTypes(BaseOrderTypes):
#     class OrderType(Enum):
#         Limit = 0
#         Market = 1

class HyperliquidOrderSides(BaseOrderSides):
    class OrderSides(Enum):
        A = 0
        B = 1
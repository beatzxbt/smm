from abc import ABC, abstractmethod
from dataclasses import dataclass

from framework.tools.logger import Logger
from framework.base.exchange import BaseExchange
from framework.base.internal_structs import OrderMsg, PositionMsg, ExecutionMsg, OrderTimeInForce


@dataclass
class DesiredOrder:
    """
    This class is used to represent an order that the strategy wants to have in the order book.
    It is not necessarily the order that will be executed, but it is the order that the strategy wants to have in the order book.

    Price and size must be pre-rounded to the exchange's precision.
    """
    cloid: str
    symbol: str
    px: float
    is_buy: bool
    sz: float


class BaseOrderManagementSystem(ABC):
    def __init__(self, exchange: BaseExchange, logger: Logger):
        self.exchange = exchange
        self.logger = logger
        self._inflight_orders = {}
        self._current_orders = {}
        self._current_position = {
            "px": 0.0,
            "is_long": True,
            "sz": 0.0,
            "age": 0.0
        }
    
    @abstractmethod
    def consume_order_event(self, event: OrderMsg) -> None:
        pass
        
    @abstractmethod
    def consume_position_event(self, event: PositionMsg) -> None:
        pass

    @abstractmethod
    def consume_execution_event(self, event: ExecutionMsg) -> None:
        pass
    
    @abstractmethod
    async def maybe_update_state(self, desired_orders: list[DesiredOrder], **kwargs):
        """
        Loops over the queued actions and applies them. This may include
        px/sz buffer checks to disguard unneccesary actions in order to 
        conserve rate limits.

        Usually, the priority actions will be executed immediately, and the
        queued actions will be executed in order.
        """
        pass

    def get_inflight_orders(self) -> dict:
        return self._inflight_orders
    
    def get_current_orders(self) -> dict:
        return self._current_orders
    
    def get_current_position(self) -> dict:
        return self._current_position
    
    async def shutdown(self, close_all_orders: bool=True, close_position: bool=True):
        """
        Cancels all inflight orders and closes all open orders.
        """
        if close_all_orders:
            self.logger.warning(f"Strategy shutting down; cancelling all orders")
            await self.exchange.cancel_all_orders(symbol=self.symbol)
        
        if close_position:
            self.logger.warning(f"Strategy shutting down; closing any outstanding position")
            
            # Take the position's size in the opposite direction.
            await self.exchange.create_order(
                symbol=self.symbol,
                is_maker=False,
                sz=self._current_position["sz"],
                is_buy=not self._current_position["is_long"],
                tif=OrderTimeInForce.GTC,
                reduce_only=True,
            )


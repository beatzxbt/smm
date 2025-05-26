from abc import ABC, abstractmethod
from dataclasses import dataclass

from framework.tools.logger import Logger
from framework.base.exchange import BaseExchange
from framework.base.internal_structs import OrderMsg, PositionMsg, ExecutionMsg, OrderTimeInForce


@dataclass
class DesiredOrder:
    """Represents an order that the strategy wants to have in the order book.
    
    This class is used to represent an order that the strategy wants to have in the order book.
    It is not necessarily the order that will be executed, but it is the order that the strategy wants to have in the order book.

    Price and size must be pre-rounded to the exchange's precision.
    
    Attributes:
        cloid: Client order ID for the order.
        symbol: Trading symbol for the order.
        px: Price for the order.
        is_buy: True if this is a buy order, False for sell.
        sz: Size/quantity for the order.
    """
    cloid: str
    symbol: str
    px: float
    is_buy: bool
    sz: float


class BaseOrderManagementSystem(ABC):
    """Base class for order management systems.
    
    This abstract class defines the interface for order management systems that handle
    order lifecycle, position tracking, and execution management.
    
    Attributes:
        exchange: The exchange interface for order operations.
        logger: Logger instance for logging messages.
    """
    
    def __init__(self, exchange: BaseExchange, logger: Logger):
        """Initialize the order management system.
        
        Args:
            exchange: The exchange interface for order operations.
            logger: Logger instance for logging messages.
        """
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
        """Process an order event.
        
        Args:
            event: Order message containing order update data.
        """
        pass
        
    @abstractmethod
    def consume_position_event(self, event: PositionMsg) -> None:
        """Process a position event.
        
        Args:
            event: Position message containing position update data.
        """
        pass

    @abstractmethod
    def consume_execution_event(self, event: ExecutionMsg) -> None:
        """Process an execution event.
        
        Args:
            event: Execution message containing execution data.
        """
        pass
    
    @abstractmethod
    async def maybe_update_state(self, desired_orders: list[DesiredOrder], **kwargs):
        """Update the order management state based on desired orders.
        
        Loops over the queued actions and applies them. This may include
        px/sz buffer checks to disguard unneccesary actions in order to 
        conserve rate limits.

        Usually, the priority actions will be executed immediately, and the
        queued actions will be executed in order.
        
        Args:
            desired_orders: List of orders that the strategy wants to have active.
            **kwargs: Additional keyword arguments.
        """
        pass

    def get_inflight_orders(self) -> dict:
        """Get the current inflight orders.
        
        Returns:
            Dictionary containing inflight orders.
        """
        return self._inflight_orders
    
    def get_current_orders(self) -> dict:
        """Get the current active orders.
        
        Returns:
            Dictionary containing current active orders.
        """
        return self._current_orders
    
    def get_current_position(self) -> dict:
        """Get the current position information.
        
        Returns:
            Dictionary containing current position data including price, direction, size, and age.
        """
        return self._current_position
    
    async def shutdown(self, close_all_orders: bool=True, close_position: bool=True):
        """Shutdown the order management system.
        
        Cancels all inflight orders and closes all open orders.
        
        Args:
            close_all_orders: Whether to cancel all open orders. Defaults to True.
            close_position: Whether to close any outstanding position. Defaults to True.
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

import asyncio
from abc import ABC, abstractmethod

from framework.tools.round import Round
from framework.tools.logger import Logger
from framework.tools.time import time_s

from framework.base.exchange import BaseExchange
from framework.base.internal_structs import HealthCheckMsg, Event

from smm.strategies.base.oms import BaseOrderManagementSystem
from smm.strategies.base.engine import BaseFeatureEngine

class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    This class provides the common functionality and interface that all
    strategy implementations must follow.
    """
    
    def __init__(
            self, 
            exchange: BaseExchange, 
            params: dict, 
            logger: Logger, 
            producer_queues: list[asyncio.Queue], 
            oms: BaseOrderManagementSystem, 
            feature_engine: BaseFeatureEngine
        ):
        """
        Initialize the base strategy with common components.
        
        Args:
            exchange (BaseExchange): Exchange client for executing trades.
            params (dict): Strategy configuration parameters.
            logger (Logger): Logger instance for recording activity.
            producer_queues (list[asyncio.Queue]): Queues for receiving market data events.
            oms (BaseOrderManagementSystem): Order management system for executing trades.
            feature_engine (BaseFeatureEngine): Feature engine for extracting features from market data.
        Raises:
            ValueError: If required parameters are missing from the configuration.
        """
        self.exchange = exchange
        self.params = params
        self.symbol = params["symbol"]
        self.logger = logger
        self.round = None
        
        self.oms = oms
        self.feature_engine = feature_engine
        # As mentioned in 'main.py', the first queue is reserved for the strategy solely.
        # Thus, its hardcoded here to make it simpler to pull from the queue.
        self.producer_queue = producer_queues[0]
    
        # Check for common required parameters across all strategies
        if "total_orders" not in self.params["parameters"]:
            raise ValueError("Missing parameter; expected 'total_orders'")
        if "max_usd_position" not in self.params["parameters"]:
            raise ValueError("Missing parameter; expected 'max_usd_position'")
        
        # Track health check. Should be cancelled/started on a rolling basis
        # as new health check events are received.
        self._health_check_task = None

    def add_rounder(self, tick_sz: float, lot_sz: float):
        """
        Add a rounder to the strategy.
        """
        self.round = Round(tick_sz, lot_sz)

    async def track_health_check(self, event: HealthCheckMsg, buffer_s: float=1.0):
        """
        Track health check events to ensure system connectivity.
        
        Given an initial health check event, sets a timer for the next expected
        health check. If a new health check event is received before the timer expires,
        this task will be cancelled and a new one scheduled. If the timer expires,
        the strategy will be halted with an exception.
        
        Args:
            event (HealthCheckMsg): The health check event containing timing information.
            buffer_s (float, optional): Additional buffer time in seconds. Defaults to 1.0.
            
        Raises:
            ValueError: If the next check time is not in the future.
            ConnectionError: If the health check timer expires without a new event.
        """
        self.logger.debug(f"Tracking health check for {event.id}; next_check={event.next_check}")

        time_to_next_check = event.next_check - time_s() + buffer_s
        if time_to_next_check <= 0:
            raise ValueError(f"Invalid {event.id} health check timestamp; expected 'next_check' to be in the future but got '{event.next_check}'")
        
        try:
            while True:
                await asyncio.sleep(time_to_next_check)
                raise ConnectionError(f"{event.id} health check timed out;")
        except asyncio.CancelledError:
            self.logger.debug(f"Health check tracking for {event.id} cancelled;")
            return
    
    @abstractmethod
    async def consume_event(self, event: Event, **kwargs):
        """
        Process an incoming event from the market data stream.
        
        Args:
            event (Event): The event to process.
            **kwargs: Additional keyword arguments.
            
        Returns:
            Implementation dependent.
        """
        pass
    
    @abstractmethod
    async def update_state(self, **kwargs):
        """
        Update the live state of the strategy.
        
        Args:
            **kwargs: Additional keyword arguments.
            
        Returns:
            Implementation dependent.
        """
        pass
    
    @abstractmethod
    async def start(self):
        """
        Start the strategy's main execution loop.
        
        Returns:
            Implementation dependent.
        """
        pass
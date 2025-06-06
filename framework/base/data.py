import asyncio
import msgspec
import aiohttp
from abc import ABC, abstractmethod

from framework.tools.logger import Logger
from framework.tools.time import time_s

from framework.base.internal_structs import (
    Symbol,
    Exchange,
    HeartbeatMsg,
    Event
)

class BaseMarketData(ABC):
    """Base class for market data handling.
    
    This abstract class provides the foundation for handling market data streams,
    including connection management, data processing, and distribution to consumers.
    """
    
    def __init__(
            self, 
            exchange: Exchange, 
            symbols: list[Symbol], 
            logger: Logger, 
            consumer_queues: list[asyncio.Queue]
        ) -> None:
        """Initialize the base market data handler.
        
        Args:
            exchange (Exchange): The exchange to subscribe to.
            symbols (list[Symbol]): The trading symbols to subscribe to.
            logger (Logger): Logger instance for logging events and errors.
            consumer_queues (list[asyncio.Queue]): List of queues for sending data to the consumer modules.
        """
        self.exchange = exchange
        self.symbols = set(symbols)
        self.logger = logger
        self.consumer_queues = consumer_queues

        self.json_decoder = msgspec.json.Decoder()
        self.json_encoder = msgspec.json.Encoder()

        # Have this running in the background from the get-go
        asyncio.create_task(self.broadcast_heartbeat())

    def broadcast(self, msg: Event):
        """Broadcast a message to all consumer queues.
        
        Args:
            msg (Event): The structured message to broadcast to all consumers.
        """
        for queue in self.consumer_queues:
            # We can nowait as there's no max size limit
            queue.put_nowait(self.json_encoder.encode(msg))

    async def broadcast_heartbeat(self, interval: int=60):
        """Broadcast a heartbeat message to all consumer queues.
        
        Args:
            interval (int, optional): The interval in seconds between heartbeat messages. Defaults to 60.
        """
        while True:
            await asyncio.sleep(interval)
            time_now = time_s()
            heartbeat_msg = HeartbeatMsg(
                exchange=self.exchange,
                time=time_now,
                next_check=time_now + interval
            )
            self.broadcast(heartbeat_msg)
            self.logger.debug(f"Broadcasting heartbeat from market data feed; {heartbeat_msg}")

    @abstractmethod
    async def process_ticker(self, data: dict):
        """Process ticker data.
        
        Args:
            data (dict): The raw ticker data to process.
            
        Note:
            The processed data must be distributed via self.broadcast(msg).
        """
        pass
    
    @abstractmethod
    async def process_orderbook(self, data: dict):
        """Process orderbook data.
        
        Args:
            data (dict): The raw orderbook data to process.
            
        Note:
            The processed data must be distributed via self.broadcast(msg).
        """
        pass
    
    @abstractmethod
    async def process_trade(self, data: dict):
        """Process trade data.
        
        Args:
            data (dict): The raw trade data to process.
            
        Note:
            The processed data must be distributed via self.broadcast(msg).
        """
        pass

    @abstractmethod
    async def start(self):
        """Open and maintain the market data connection.
        
        This method should handle establishing the connection, subscribing to relevant
        channels, and maintaining the connection with appropriate error handling and
        reconnection logic.
        """
        pass

class BasePrivateData(ABC):
    """Base class for handling private data streams.
    
    Manages connection, subscription, and processing of private data like orders and positions.
    Requires authentication with API credentials to access user-specific data.
    """
    def __init__(
            self, 
            exchange: Exchange, 
            api_key: str, 
            api_secret: str, 
            symbols: list[str], 
            logger: Logger, 
            consumer_queues: list[asyncio.Queue]
        ):
        """Initialize the base private data handler.
        
        Args:
            exchange (Exchange): The exchange to subscribe to.
            api_key (str): API key for authentication with the exchange.
            api_secret (str): API secret for authentication with the exchange.
            symbols (list[str]): The trading symbols to subscribe to.
            logger (Logger): Logger instance for logging events and errors.
            consumer_queues (list[asyncio.Queue]): List of queues for sending data to the consumer modules.
        """
        self.exchange = exchange
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbols = set(symbols)
        self.logger = logger
        self.consumer_queues = consumer_queues

        self.json_decoder = msgspec.json.Decoder()
        self.json_encoder = msgspec.json.Encoder()

        # Have this running in the background from the get-go
        asyncio.create_task(self.broadcast_heartbeat())

    def broadcast(self, msg: msgspec.Struct):
        """Broadcast a message to all consumer queues.
        
        Args:
            msg (msgspec.Struct): The structured message to broadcast to all consumers.
        """
        for queue in self.consumer_queues:
            # We can nowait as there's no max size limit
            queue.put_nowait(self.json_encoder.encode(msg))

    async def broadcast_heartbeat(self, interval: int=60):
        """Broadcast a health check message to all consumer queues.
        
        Args:
            interval (int, optional): The interval in seconds between heartbeat messages. Defaults to 60.
        """
        while True:
            await asyncio.sleep(interval)
            time_now = time_s()
            heartbeat_msg = HeartbeatMsg(
                exchange=self.exchange,
                time=time_now,
                next_check=time_now + interval
            )
            self.broadcast(heartbeat_msg)
            self.logger.debug(f"Broadcasting heartbeat from private data feed; {heartbeat_msg}")

    @abstractmethod
    async def process_order(self, data: dict):
        """Process order data.
        
        Args:
            data (dict): The raw order data to process.
            
        Note:
            The processed data must be distributed via self.broadcast(msg).
        """
        pass
    
    @abstractmethod
    async def process_position(self, data: dict):
        """Process position data.
        
        Args:
            data (dict): The raw position data to process.
            
        Note:
            The processed data must be distributed via self.broadcast(msg).
        """
        pass

    @abstractmethod
    async def process_execution(self, data: dict):
        """Process execution data.
        
        Args:
            data (dict): The raw execution data to process.
            
        Note:
            The processed data must be distributed via self.broadcast(msg).
        """
        pass

    @abstractmethod
    async def process_account(self, data: dict):
        """Process account data.
        
        Args:
            data (dict): The raw account data to process.
            
        Note:
            The processed data must be distributed via self.broadcast(msg).
        """
        pass

    @abstractmethod 
    async def authenticate(self, ws: aiohttp.ClientWebSocketResponse):
        """Authenticate the WebSocket connection.
        
        Args:
            ws (aiohttp.ClientWebSocketResponse): The WebSocket connection to authenticate.
            
        Returns:
            bool: True if authentication was successful, False otherwise.
            
        Raises:
            ConnectionError: If the WebSocket connection is not initialized.
        """
        pass
    
    @abstractmethod
    async def start(self):
        """Connect to the private data stream.
        
        This method should handle establishing the connection, authenticating,
        subscribing to relevant private channels, and maintaining the connection
        with appropriate error handling and reconnection logic.
        """
        pass

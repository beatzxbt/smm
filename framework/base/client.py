import aiohttp
import asyncio
import msgspec
from abc import ABC, abstractmethod
from typing import Union, Literal

from framework.tools.logger import Logger

class BaseRestTradeClient(ABC):
    """Base class for REST API clients"""
    
    def __init__(self, api_key: str, api_secret: str, logger: Logger):
        """
        Initialize the base client.
        
        Args:
            api_key (str): Bybit API key.
            api_secret (str): Bybit API secret.
            logger (Logger): Logger instance.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.logger = logger

        self.ev_loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession()

        self.is_running = True

        self.json_encoder = msgspec.json.Encoder()
        self.json_decoder = msgspec.json.Decoder()

    def ensure_running(self, throw_exc: bool = True) -> bool:
        """Ensure the client is running.
        
        Args:
            throw_exc (bool, optional): If True, raise a ConnectionError if the client is not running.
                Defaults to True.
        
        Returns:
            bool: True if the client is running, False otherwise.
        """
        if not self.is_running:
            self.logger.error("RestTradeClient is not running;")
            if throw_exc:
                raise ConnectionError("RestTradeClient is not running;")
            return False
        return True
    
    @abstractmethod
    def sign(self, payload_str: str) -> dict:
        """Sign the payload"""
        pass
    
    @abstractmethod
    async def submit(self, endpoint: str, payload: dict, method: Union[Literal["POST"], Literal["GET"], Literal["PUT"], Literal["DELETE"]] = "POST"):
        """Submit the request"""
        pass
    
    async def close(self):
        """Close the client session"""
        if self.is_running:
            await self.session.close()
            self.logger.info(f"Trade REST client connection closed")
            self.is_running = False


class BaseWsTradeClient(ABC):
    """Base class for WebSocket API clients"""
    
    def __init__(self, api_key: str, api_secret: str, logger: Logger):
        """
        Initialize the base client.
        
        Args:
            api_key (str): Bybit API key.
            api_secret (str): Bybit API secret.
            logger (Logger): Logger instance.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.logger = logger

        self.ev_loop = asyncio.get_event_loop()
        self.session = aiohttp.ClientSession()

        self.json_encoder = msgspec.json.Encoder()
        self.json_decoder = msgspec.json.Decoder()

        self.is_running = False

    @abstractmethod
    async def authenticate(self, ws: aiohttp.ClientWebSocketResponse) -> bool:
        """Authenticate the client"""
        pass
    
    @abstractmethod
    async def heartbeat(self):
        """Send a heartbeat"""
        pass
    
    @abstractmethod
    async def connect(self):
        """Connect to the WebSocket"""
        pass
    
    @abstractmethod
    async def submit(self, payload: dict) -> dict:
        """Submit a request"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close the client session"""
        pass

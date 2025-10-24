from abc import ABC, abstractmethod
from enum import StrEnum
from typing import final

import aiohttp
import msgspec

from framework.base.common import Venue
from framework.base.tools import Logger
from framework.base.trading.structs import ClientResponse


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class HttpClient(ABC):
    """Base class for HTTP API clients."""

    def __init__(self, venue: Venue, logger: Logger):
        """Initialize the base client."""
        self.venue = venue
        self.logger = logger

        self.session = aiohttp.ClientSession()

        self.is_running = True

    @final
    def ensure_running(self, throw_exc: bool = True) -> bool:
        """Ensure the client is running."""
        if not self.is_running:
            self.logger.error(f"{self.__class__.__name__} is not running; {self.venue}")
            if throw_exc:
                raise ConnectionError(
                    f"{self.__class__.__name__} is not running; {self.venue}"
                )
            return False
        return True

    @abstractmethod
    def sign(self, method: HttpMethod, endpoint: str, body: dict) -> dict:
        """Generate authentication signature for requests."""
        pass

    @abstractmethod
    async def request[T](
        self,
        method: HttpMethod,
        endpoint: str,
        params: dict,
        data: dict,
        sign: bool,
        decoder: msgspec.json.Decoder[T],
    ) -> ClientResponse[T]:
        """Send an HTTP request to the exchange API."""
        pass

    @final
    async def close(self):
        """Close the client session."""
        if self.is_running:
            await self.session.close()
            self.logger.info(
                f"{self.__class__.__name__} connection closed; {self.venue}"
            )
            self.is_running = False


class WsClient(ABC):
    """Base class for WebSocket API clients."""

    def __init__(self, venue: Venue, logger: Logger):
        """Initialize the base client."""
        self.venue = venue
        self.logger = logger

        self.session = aiohttp.ClientSession()

        self.is_running = False

    @abstractmethod
    async def authenticate(self, ws: aiohttp.ClientWebSocketResponse) -> bool:
        """Authenticate the client."""
        pass

    @abstractmethod
    async def heartbeat(self):
        """Send a heartbeat."""
        pass

    @abstractmethod
    async def connect(self):
        """Connect to the WebSocket."""
        pass

    @abstractmethod
    async def submit[T](
        self, data: dict, decoder: msgspec.json.Decoder[T]
    ) -> ClientResponse[T]:
        """Submit a request."""
        pass

    @final
    async def close(self):
        """Close the client session."""
        if self.is_running:
            await self.session.close()
            self.logger.info(
                f"{self.__class__.__name__} connection closed; {self.venue}"
            )
            self.is_running = False

"""Base HTTP and WebSocket client abstractions.

Defines shared session management, lifecycle helpers, and JSON encoding utilities
for exchange clients.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import final

import aiohttp
import msgspec

from framework.base.common import Venue
from mm_toolbox.logging.standard import Logger
from framework.base.trading.models import ClientResponse


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class HttpClient(ABC):
    """Base class for HTTP API clients."""

    def __init__(self, venue: Venue, logger: Logger, load_secrets: bool):
        """Initialize the base client."""
        self.venue = venue
        self.logger = logger
        self.load_secrets = load_secrets

        self._json_encoder = msgspec.json.Encoder()
        self._session: aiohttp.ClientSession | None = None

        self.is_running = True

    @final
    def ensure_running(self, throw_exc: bool = True) -> bool:
        """Ensure the client is running."""
        if not self.is_running:
            self.logger.error(
                f"{self.__class__.__name__}.ensure_running error; not running; {self.venue}"
            )
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
            if self._session and not self._session.closed:
                await self._session.close()
            self.logger.info(
                f"{self.__class__.__name__}.close connection closed; {self.venue}"
            )
            self.is_running = False

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session


class WsClient(ABC):
    """Base class for WebSocket API clients."""

    def __init__(self, venue: Venue, logger: Logger, load_secrets: bool):
        """Initialize the base client."""
        self.venue = venue
        self.logger = logger
        self.load_secrets = load_secrets

        self._json_encoder = msgspec.json.Encoder()
        self._session: aiohttp.ClientSession | None = None

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

    async def close(self):
        """Close the client session."""
        if self.is_running:
            if self._session and not self._session.closed:
                await self._session.close()
            self.logger.info(
                f"{self.__class__.__name__}.close connection closed; {self.venue}"
            )
            self.is_running = False

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

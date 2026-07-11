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
from framework.base.trading.models import (
    ClientResponse,
    ClientResponseFailure,
    ClientResponseMeta,
    ClientResponseSuccess,
    ClientResponseTransport,
)
from framework.base.trading.time_sync import TimeSync
from mm_toolbox.logging.standard import Logger


def _coerce_failure_error(err_no: int, err_msg: str) -> tuple[int, str]:
    """Normalize failure error details to satisfy response invariants.

    Args:
        err_no: Error code for the failure.
        err_msg: Error message for the failure.

    Returns:
        tuple[int, str]: Normalized error code and message.
    """
    if err_no == 0 and err_msg == "":
        return 1, "Unknown error"
    return err_no, err_msg


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class HttpClient(ABC):
    """Base class for HTTP API clients."""

    def __init__(
        self, venue: Venue, logger: Logger, load_secrets: bool, time_sync: TimeSync
    ):
        """Initialize the base client."""
        self.venue = venue
        self.logger = logger
        self.load_secrets = load_secrets
        self.time_sync = time_sync

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
    def make_meta(
        self,
        *,
        transport: ClientResponseTransport,
        operation: str,
        started_ns: int,
        finished_ns: int | None = None,
        request_id: str | None = None,
        status_code: int | None = None,
        attempt: int = 1,
        timeout: bool = False,
    ) -> ClientResponseMeta:
        """Create metadata for a request/response lifecycle.

        Args:
            transport: Transport type used for the request.
            operation: Full endpoint or operation name.
            started_ns: Request start timestamp in nanoseconds.
            finished_ns: Request finish timestamp in nanoseconds.
            request_id: Optional transport-specific request identifier.
            status_code: Optional transport/application status code.
            attempt: One-based retry attempt counter.
            timeout: Whether the result was produced by a timeout.

        Returns:
            ClientResponseMeta: Metadata attached to the client response.
        """
        end_ns = started_ns if finished_ns is None else finished_ns
        return ClientResponseMeta(
            started_ns=started_ns,
            finished_ns=end_ns,
            venue=self.venue,
            transport=transport,
            operation=operation,
            request_id=request_id,
            status_code=status_code,
            attempt=attempt,
            timeout=timeout,
        )

    @final
    def make_success[T](
        self, *, data: T, meta: ClientResponseMeta
    ) -> ClientResponse[T]:
        """Create a successful client response.

        Args:
            data: Typed payload returned by the request.
            meta: Metadata envelope for the request lifecycle.

        Returns:
            ClientResponse[T]: Successful response variant.
        """
        return ClientResponseSuccess(data=data, meta=meta)

    @final
    def make_failure[T](
        self,
        *,
        meta: ClientResponseMeta,
        err_no: int = 1,
        err_msg: str = "",
    ) -> ClientResponse[T]:
        """Create a failed client response.

        Args:
            meta: Metadata envelope for the request lifecycle.
            err_no: Numeric error code for the failure.
            err_msg: Human-readable failure message.

        Returns:
            ClientResponse[T]: Failed response variant.
        """
        normalized_err_no, normalized_err_msg = _coerce_failure_error(err_no, err_msg)
        return ClientResponseFailure(
            meta=meta,
            err_no=normalized_err_no,
            err_msg=normalized_err_msg,
        )

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

    def __init__(
        self, venue: Venue, logger: Logger, load_secrets: bool, time_sync: TimeSync
    ):
        """Initialize the base client."""
        self.venue = venue
        self.logger = logger
        self.load_secrets = load_secrets
        self.time_sync = time_sync

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

    @final
    def make_meta(
        self,
        *,
        transport: ClientResponseTransport,
        operation: str,
        started_ns: int,
        finished_ns: int | None = None,
        request_id: str | None = None,
        status_code: int | None = None,
        attempt: int = 1,
        timeout: bool = False,
    ) -> ClientResponseMeta:
        """Create metadata for a request/response lifecycle.

        Args:
            transport: Transport type used for the request.
            operation: Full endpoint or operation name.
            started_ns: Request start timestamp in nanoseconds.
            finished_ns: Request finish timestamp in nanoseconds.
            request_id: Optional transport-specific request identifier.
            status_code: Optional transport/application status code.
            attempt: One-based retry attempt counter.
            timeout: Whether the result was produced by a timeout.

        Returns:
            ClientResponseMeta: Metadata attached to the client response.
        """
        end_ns = started_ns if finished_ns is None else finished_ns
        return ClientResponseMeta(
            started_ns=started_ns,
            finished_ns=end_ns,
            venue=self.venue,
            transport=transport,
            operation=operation,
            request_id=request_id,
            status_code=status_code,
            attempt=attempt,
            timeout=timeout,
        )

    @final
    def make_success[T](
        self, *, data: T, meta: ClientResponseMeta
    ) -> ClientResponse[T]:
        """Create a successful client response.

        Args:
            data: Typed payload returned by the request.
            meta: Metadata envelope for the request lifecycle.

        Returns:
            ClientResponse[T]: Successful response variant.
        """
        return ClientResponseSuccess(data=data, meta=meta)

    @final
    def make_failure[T](
        self,
        *,
        meta: ClientResponseMeta,
        err_no: int = 1,
        err_msg: str = "",
    ) -> ClientResponse[T]:
        """Create a failed client response.

        Args:
            meta: Metadata envelope for the request lifecycle.
            err_no: Numeric error code for the failure.
            err_msg: Human-readable failure message.

        Returns:
            ClientResponse[T]: Failed response variant.
        """
        normalized_err_no, normalized_err_msg = _coerce_failure_error(err_no, err_msg)
        return ClientResponseFailure(
            meta=meta,
            err_no=normalized_err_no,
            err_msg=normalized_err_msg,
        )

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
